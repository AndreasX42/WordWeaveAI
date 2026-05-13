import json
import os
from dataclasses import dataclass
from enum import Enum
from typing import Any

from aws_lambda_powertools import Logger
from pydantic import BaseModel, Field

from vocab_processor.constants import LLMVariant
from vocab_processor.prompts import build_supervisor_tool_validation_prompt
from vocab_processor.schemas.media_model import SearchQueryResult
from vocab_processor.tools.base_tool import SystemMessages, create_llm_response
from vocab_processor.tools.classification_tool import WordClassification
from vocab_processor.tools.conjugation_tool import ConjugationResponse
from vocab_processor.tools.examples_tool import Examples
from vocab_processor.tools.syllables_tool import SyllableBreakdown
from vocab_processor.tools.synonyms_tool import Synonyms
from vocab_processor.tools.translation_tool import Translation
from vocab_processor.tools.validation_tool import WordValidationResult
from vocab_processor.utils.state import VocabState

logger = Logger(service="vocab-processor-supervisor")


def _supervisor_float(key: str, default: float) -> float:
    raw = os.getenv(key)
    if raw is None or not str(raw).strip():
        return default
    return float(raw)


def _supervisor_int(key: str, default: int) -> int:
    raw = os.getenv(key)
    if raw is None or not str(raw).strip():
        return default
    return int(raw)


class TaskType(str, Enum):
    """Types of tasks for LLM routing."""

    SUPERVISION = "supervision"
    VALIDATION = "validation"
    QUALITY_CHECK = "quality_check"
    TRANSLATION = "translation"
    EXAMPLES = "examples"
    SYNONYMS = "synonyms"
    SYLLABLES = "syllables"
    CONJUGATION = "conjugation"
    MEDIA_SELECTION = "media_selection"
    CLASSIFICATION = "classification"


TASKS_USING_SUPERVISOR_MODEL = frozenset(
    {
        TaskType.VALIDATION,
        TaskType.QUALITY_CHECK,
    }
)

TASKS_UPGRADING_MODEL_ON_RETRY = frozenset(
    {
        TaskType.CLASSIFICATION,
        TaskType.TRANSLATION,
        TaskType.EXAMPLES,
        TaskType.SYNONYMS,
        TaskType.SYLLABLES,
        TaskType.CONJUGATION,
        TaskType.MEDIA_SELECTION,
    }
)


@dataclass(frozen=True)
class QualityGatedToolSpec:
    """Per-tool metadata for supervisor quality checks and retries."""

    output_schema: type[BaseModel]
    accepts_quality_feedback: bool = True


QUALITY_GATED_TOOLS: dict[str, QualityGatedToolSpec] = {
    "validation": QualityGatedToolSpec(WordValidationResult),
    "classification": QualityGatedToolSpec(WordClassification),
    "translation": QualityGatedToolSpec(Translation),
    "examples": QualityGatedToolSpec(Examples),
    "synonyms": QualityGatedToolSpec(Synonyms),
    "syllables": QualityGatedToolSpec(SyllableBreakdown),
    "conjugation": QualityGatedToolSpec(ConjugationResponse),
    "media": QualityGatedToolSpec(SearchQueryResult),
}

TOOLS_SKIPPING_QUALITY_VALIDATION: frozenset[str] = frozenset({"pronunciation"})

TOOLS_ACCEPTING_QUALITY_FEEDBACK: frozenset[str] = frozenset(
    name for name, spec in QUALITY_GATED_TOOLS.items() if spec.accepts_quality_feedback
)

PARALLEL_TOOL_CORE: tuple[str, ...] = ("media", "examples", "synonyms", "syllables")


def expected_parallel_task_names(state: VocabState) -> list[str]:
    """Parallel branch ids that match `agent.build_vocab_graph` fan-out."""

    names = list(PARALLEL_TOOL_CORE)
    if state.target_part_of_speech and state.target_part_of_speech.is_conjugatable:
        names.append("conjugation")
    names.append("pronunciation")
    return names


class ToolValidationResult(BaseModel):
    """Result of tool output validation."""

    score: float = Field(..., ge=0.0, le=10.0, description="Quality score from 0-10")
    issues: list[str] = Field(
        default=[],
        description="List of clearly and unambiguously formulated identified issues",
    )
    suggestions: list[str] = Field(
        default=[],
        description="List of clear and targeted improvement suggestions to improve the quality of the output",
    )


class RetryStrategy(BaseModel):
    """Strategy for retrying failed tools."""

    should_retry: bool = Field(...)
    retry_reason: str = Field(...)
    adjusted_inputs: dict[str, Any] = Field(default={})


def _is_pexels_photo_src_bundle(photos_src: dict[Any, Any]) -> bool:
    return set(photos_src.keys()) == {"large2x", "large", "medium"} and all(
        isinstance(v, str) and v.startswith("https://") and v.endswith(".jpg")
        for v in photos_src.values()
    )


def _preflight_media_tool_validation(
    result: Any,
    prompt: str,
) -> ToolValidationResult | tuple[Any, str]:
    """Return a final validation result or (normalized_result, prompt) for LLM scoring."""

    if isinstance(result, dict) and result.get("api_fallback"):
        logger.info("Media tool used API fallback - accepting with good score")
        return ToolValidationResult(score=10.0, issues=[], suggestions=[])

    if isinstance(result, dict):
        media = result.get("media")
        photos_src = None
        if hasattr(media, "src"):
            photos_src = media.src
        elif isinstance(media, dict):
            photos_src = media.get("src")

        if isinstance(photos_src, dict) and _is_pexels_photo_src_bundle(photos_src):
            return ToolValidationResult(score=10.0, issues=[], suggestions=[])

    if isinstance(result, dict) and "search_query" in result:
        normalized_prompt = result.get("search_query_prompt") or prompt
        wrapped = {"search_query": result["search_query"]}
        return wrapped, normalized_prompt

    logger.warning("Media tool output format unexpected, skipping validation.")
    return ToolValidationResult(score=10.0, issues=[], suggestions=[])


class LLMRouter:
    """Smart routing between expensive and cheap models."""

    @staticmethod
    def get_model_for_task(task_type: TaskType, num_retries: int) -> LLMVariant:
        """Select appropriate LLM model based on task complexity."""

        if task_type in TASKS_USING_SUPERVISOR_MODEL:
            return LLMVariant.SUPERVISOR
        if task_type in TASKS_UPGRADING_MODEL_ON_RETRY:
            return (
                LLMVariant.SUPERVISOR
                if num_retries > 1
                else LLMVariant.NODE_EXECUTOR
            )
        return LLMVariant.NODE_EXECUTOR


class VocabSupervisor:
    """Supervisor for vocabulary processing quality control."""

    def __init__(
        self,
        quality_threshold: float,
        max_retries: int,
        final_attempt_min_score: float,
    ):
        self.quality_threshold = quality_threshold
        self.max_retries = max_retries
        self.final_attempt_min_score = final_attempt_min_score
        self.router = LLMRouter()

        self.skip_validation_tools = TOOLS_SKIPPING_QUALITY_VALIDATION
        self.tool_schemas = {
            name: spec.output_schema for name, spec in QUALITY_GATED_TOOLS.items()
        }

    def _serialize_tool_result_for_prompt(self, result: Any) -> str:
        if isinstance(result, BaseModel):
            return result.model_dump_json(indent=2)
        try:
            return json.dumps(result, indent=2)
        except TypeError:
            return str(result)

    async def validate_tool_output(
        self, tool_name: str, result: Any, state: VocabState, prompt: str
    ) -> ToolValidationResult:
        """Schema-aware validation of tool outputs."""

        if tool_name in self.skip_validation_tools:
            return ToolValidationResult(score=10.0, issues=[], suggestions=[])

        if tool_name == "media":
            media_outcome = _preflight_media_tool_validation(result, prompt)
            if isinstance(media_outcome, ToolValidationResult):
                return media_outcome
            result, prompt = media_outcome

        spec = QUALITY_GATED_TOOLS.get(tool_name)
        if spec is None:
            raise ValueError(f"Unknown tool: {tool_name}")

        schema_block = json.dumps(spec.output_schema.model_json_schema(), indent=2)
        result_json_str = self._serialize_tool_result_for_prompt(result)
        source_language_display = (
            state.source_language.value if state.source_language else "unknown"
        )
        target_language_display = state.target_language.value

        validation_prompt = build_supervisor_tool_validation_prompt(
            source_word=state.source_word,
            source_language_display=source_language_display,
            target_word=state.target_word or "",
            target_language_display=target_language_display,
            tool_name=tool_name,
            schema_json_block=schema_block,
            assistant_prompt=prompt,
            assistant_output_json=result_json_str,
            quality_threshold=self.quality_threshold,
        )

        try:
            validation_result = await create_llm_response(
                response_model=ToolValidationResult,
                user_prompt=validation_prompt,
                system_message=SystemMessages.VALIDATION_SPECIALIST,
                llm_provider=self.router.get_model_for_task(
                    TaskType.QUALITY_CHECK,
                    num_retries=0,
                ),
            )

            if validation_result.score >= self.quality_threshold:
                validation_result.issues = []
                validation_result.suggestions = []

            return validation_result

        except Exception as e:
            logger.error(
                "supervisor_quality_llm_failed",
                tool_name=tool_name,
                error=str(e),
            )
            return ToolValidationResult(score=10.0, issues=[], suggestions=[])

    async def plan_retry_strategy(
        self,
        tool_name: str,
        validation_result: ToolValidationResult,
        state: VocabState,
    ) -> RetryStrategy:
        """Determine retry strategy based on validation results."""

        retry_count = getattr(state, f"{tool_name}_retry_count", 0)

        if validation_result.score >= self.quality_threshold:
            return RetryStrategy(
                should_retry=False,
                retry_reason="Score meets quality threshold",
                adjusted_inputs={},
            )

        if retry_count >= self.max_retries:
            if validation_result.score >= self.final_attempt_min_score:
                return RetryStrategy(
                    should_retry=False,
                    retry_reason=(
                        f"Final retry with acceptable score (>="
                        f" {self.final_attempt_min_score})"
                    ),
                    adjusted_inputs={},
                )
            return RetryStrategy(
                should_retry=False,
                retry_reason="Maximum retries reached",
                adjusted_inputs={},
            )

        adjusted_inputs = {}

        if tool_name in TOOLS_ACCEPTING_QUALITY_FEEDBACK:
            if validation_result.issues or validation_result.suggestions:
                adjusted_inputs["quality_feedback"] = (
                    f"Quality score: {validation_result.score}/10. "
                    "Please address the issues and follow the suggestions below."
                )
                adjusted_inputs["previous_issues"] = validation_result.issues
                adjusted_inputs["suggestions"] = validation_result.suggestions

        should_retry = retry_count < self.max_retries and (
            validation_result.score < self.quality_threshold
        )

        retry_reason = (
            f"Quality score {validation_result.score} below threshold "
            f"{self.quality_threshold}"
            + (
                f". Issues: {'; '.join(validation_result.issues)}"
                if validation_result.issues
                else ""
            )
        )

        return RetryStrategy(
            should_retry=should_retry,
            retry_reason=retry_reason,
            adjusted_inputs=adjusted_inputs,
        )

    async def should_proceed_with_parallel_execution(self, state: VocabState) -> bool:
        """Determine if state is ready for parallel tool execution."""

        required_fields = [
            "source_word",
            "target_word",
            "source_language",
            "target_language",
        ]

        for field in required_fields:
            if not getattr(state, field, None):
                logger.warning(
                    f"Missing required field for parallel execution: {field}"
                )
                return False

        quality_fields = [
            "validation_passed",
            "classification_quality_approved",
            "translation_quality_approved",
        ]

        for field in quality_fields:
            if not getattr(state, field, False):
                logger.warning(f"Quality gate not passed: {field}")
                return False

        return True

    async def coordinate_parallel_tasks(self, state: VocabState) -> list[str]:
        """Determine which parallel tasks should be executed."""

        return expected_parallel_task_names(state)


supervisor = VocabSupervisor(
    quality_threshold=_supervisor_float("VOCAB_QUALITY_THRESHOLD", 7.5),
    max_retries=_supervisor_int("VOCAB_QUALITY_MAX_RETRIES", 2),
    final_attempt_min_score=_supervisor_float("VOCAB_QUALITY_FINAL_MIN_SCORE", 6.5),
)


def create_fallback_result(
    tool_name: str, inputs: dict[str, Any], error: str
) -> dict[str, Any]:
    """Create a fallback result when tool execution fails completely."""

    logger.error(f"Creating fallback result for {tool_name}: {error}")

    fallback_results = {
        "validation": {
            "is_valid": False,
            "source_language": None,
            "error_message": f"ERROR - Validation tool failed: {error}",
            "suggestions": [],
        },
        "classification": {
            "source_word": inputs.get("source_word", "word"),
            "source_definition": ["Definition unavailable"],
            "source_part_of_speech": "verb",
            "source_article": None,
        },
        "translation": {
            "target_word": f"ERROR - Translation tool failed: {error}",
            "target_part_of_speech": "verb",
            "target_article": None,
        },
        "media": {
            "media": {
                "url": f"ERROR - Media tool failed: {error}",
                "alt": f"Image unavailable for {inputs.get('target_word', 'word')}",
                "src": {"large2x": "", "large": "", "medium": ""},
                "explanation": "Unable to generate image at this time.",
                "memory_tip": "Try visualizing the word concept in your mind.",
            },
            "english_word": inputs.get("target_word", "word"),
            "search_query": [],
            "media_reused": False,
        },
        "examples": {
            "examples": [
                {
                    "original": f"Example with {inputs.get('source_word', 'word')} unavailable.",
                    "translation": f"Example with {inputs.get('target_word', 'word')} unavailable.",
                    "error_message": f"ERROR - Examples tool failed: {error}",
                }
            ]
        },
        "synonyms": {"synonyms": []},
        "syllables": {
            "syllables": [inputs.get("target_word", "word")],
            "phonetic_guide": f"ERROR - Syllables tool failed: {error}",
        },
        "pronunciation": {
            "pronunciations": {
                "audio": f"ERROR - Pronunciation tool failed: {error}",
                "syllables": None,
            }
        },
        "conjugation": {
            "conjugation": None,
            "error_message": f"ERROR - Conjugation tool failed: {error}",
        },
    }

    return fallback_results.get(
        tool_name, {"error": f"Tool {tool_name} failed: {error}"}
    )
