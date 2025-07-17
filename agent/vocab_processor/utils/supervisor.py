import json
from enum import Enum
from typing import Any

from aws_lambda_powertools import Logger
from pydantic import BaseModel, Field

from vocab_processor.constants import LLMVariant
from vocab_processor.schemas.media_model import SearchQueryResult
from vocab_processor.tools.base_tool import SystemMessages, create_llm_response
from vocab_processor.tools.classification_tool import WordClassification
from vocab_processor.tools.conjugation_tool import ConjugationResult
from vocab_processor.tools.examples_tool import Examples
from vocab_processor.tools.syllables_tool import SyllableBreakdown
from vocab_processor.tools.synonyms_tool import Synonyms
from vocab_processor.tools.translation_tool import Translation

# Import actual Pydantic models for schema-aware validation
from vocab_processor.tools.validation_tool import WordValidationResult
from vocab_processor.utils.state import VocabState

logger = Logger(service="vocab-processor-supervisor")


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


class LLMRouter:
    """Smart routing between expensive and cheap models."""

    @staticmethod
    def get_model_for_task(task_type: TaskType, num_retries: int) -> LLMVariant:
        """Select appropriate LLM model based on task complexity."""

        llm_variant = LLMVariant.NODE_EXECUTOR

        # Use powerful model for supervisor decisions
        if task_type in [
            TaskType.QUALITY_CHECK,
        ]:
            llm_variant = LLMVariant.SUPERVISOR

        # Use cheaper model for routine tool execution, upgrade on retry
        if task_type in [
            TaskType.VALIDATION,
            TaskType.CLASSIFICATION,
            TaskType.TRANSLATION,
            TaskType.EXAMPLES,
            TaskType.SYNONYMS,
            TaskType.SYLLABLES,
            TaskType.CONJUGATION,
            TaskType.MEDIA_SELECTION,
        ]:
            llm_variant = (
                LLMVariant.SUPERVISOR if num_retries > 1 else LLMVariant.NODE_EXECUTOR
            )

        return llm_variant


class VocabSupervisor:
    """Supervisor for vocabulary processing quality control."""

    def __init__(self, quality_threshold: float = 8.0, max_retries: int = 2):
        self.quality_threshold = quality_threshold
        self.max_retries = max_retries
        self.router = LLMRouter()

        # Tools that should skip quality validation
        self.skip_validation_tools = {"pronunciation"}

        # Define expected schemas for each tool with actual Pydantic models
        self.tool_schemas: dict[str, BaseModel] = {
            "validation": WordValidationResult,
            "classification": WordClassification,
            "translation": Translation,
            "examples": Examples,
            "synonyms": Synonyms,
            "syllables": SyllableBreakdown,
            "conjugation": ConjugationResult,
            "media": SearchQueryResult,
        }

    async def validate_tool_output(
        self, tool_name: str, result: Any, state: VocabState, prompt: str
    ) -> ToolValidationResult:
        """Schema-aware validation of tool outputs."""

        # Skip validation for tools that don't need it
        if tool_name in self.skip_validation_tools:
            return ToolValidationResult(score=10.0, issues=[], suggestions=[])

        # Special handling for media tool to validate only the search query part
        if tool_name == "media":
            # Check if this is a fallback response (API failure)
            if isinstance(result, dict) and result.get("api_fallback"):
                logger.info("Media tool used API fallback - accepting with good score")
                return ToolValidationResult(
                    score=10.0,
                    issues=[],
                    suggestions=[],
                )

            # If the media tool successfully retrieved photos, let it pass the quality check.
            if isinstance(result, dict):
                media = result.get("media")
                photos_src = None
                if hasattr(media, "src"):
                    photos_src = media.src
                elif isinstance(media, dict):
                    photos_src = media.get("src")

                if isinstance(photos_src, dict):
                    if set(photos_src.keys()) == {"large2x", "large", "medium"} and all(
                        v.startswith("https://") and v.endswith(".jpg")
                        for v in photos_src.values()
                    ):
                        return ToolValidationResult(
                            score=10.0, issues=[], suggestions=[]
                        )

            if isinstance(result, dict) and "search_query" in result:
                # The prompt for search query generation is passed in the result dict
                prompt = result.get("search_query_prompt")
                # The result to validate is the search query list, wrapped for the model
                result = {"search_query": result["search_query"]}
            else:
                logger.warning(
                    "Media tool output format unexpected, skipping validation."
                )
                return ToolValidationResult(score=10.0, issues=[], suggestions=[])

        # Get expected schema for the tool
        expected_schema_class = self.tool_schemas.get(tool_name)
        if not expected_schema_class:
            raise ValueError(f"Unknown tool: {tool_name}")
        else:
            # Serialize result to a JSON string for the prompt
            if isinstance(result, BaseModel):
                result_json_str = result.model_dump_json(indent=2)
            else:
                try:
                    result_json_str = json.dumps(result, indent=2)
                except TypeError:
                    result_json_str = str(result)

            validation_prompt = f"""
            **VALIDATION TASK**
            You are a language learning expert. Your task is to validate the work of a language learning assistant. The overall goal of the assistant is to create accurate and informative vocabulary learning materials.

            Context:
            Source word: '{state.source_word}' ('{state.source_language.value if state.source_language else "unknown"}')
            Target word: '{state.target_word}' ('{state.target_language.value}')
            Assistant used tool: {tool_name}

            **Assistant's Role:**
            The assistant is a language learning expert. It is tasked with creating accurate and informative vocabulary learning materials.

            **Assistant's Output:**
            The assistant's output is a JSON object that conforms to the expected schema.


            **1. Expected Output Schema:**
            The output MUST conform to this Pydantic model schema:
            --- SCHEMA START ---
            {expected_schema_class.model_json_schema()}
            --- SCHEMA END ---

            **2. Input Prompt:**
            This was the prompt given to the assistant:
            --- PROMPT START ---
            {prompt}
            --- PROMPT END ---

            **3. Assistant's Output:**
            Here is the assistants output using the above Pydantic model schema:
            --- JSON START ---
            {result_json_str}
            --- JSON END ---

            **Instructions for you, the Supervisor:**
            1.  **Schema Compliance:** First and foremost, check if the JSON output strictly complies with the Pydantic schema. Are all required fields present? Are the data types correct?

            2.  **Requirement Adherence:** Carefully read the 'REQUIREMENTS' section in the prompt. Has the assistant followed all instructions?

            3. **Content Quality:** The overall goal is to create an accurate and natural vocabulary learning material from the '{state.source_word}' ('{state.source_language}') to the target word '{state.target_word}' ('{state.target_language}'). The content of the output should be accurate, informative and helpful for learning the target word.
            
            4. **Quality Score:** Rate the output on a scale of 1-10, where 10 is perfect. The score should reflect both schema compliance and adherence to the prompt's requirements as well as content quality. A low score should be given if either is not met.

            5.  **Issues and Suggestions:**
                - If the score is below {self.quality_threshold}, you MUST provide a list of found issues. Each issue should be a clear, concise statement describing a specific failure (e.g., "Field 'x' is missing", "Translation for 'y' is unnatural", "Source word "z" as a matter of fact does exist in the source language and is used in certain parts of the world").
                - If there are issues, you MUST also provide a list of suggestions for the assistant to improve the output on the next attempt. Suggestions should be actionable and directly related to the issues found.

            Your response MUST be a valid JSON object matching the ToolValidationResult schema.
            The score should be between 1 and 10 and should reflect the accuracy and quality of the output based on the given conditions.
            """

        try:
            validation_result = await create_llm_response(
                response_model=ToolValidationResult,
                user_prompt=validation_prompt,
                system_message=SystemMessages.VALIDATION_SPECIALIST,
                llm_provider=self.router.get_model_for_task(
                    TaskType.QUALITY_CHECK, num_retries=0
                ),
            )

            # For high scores, clear issues and suggestions
            if validation_result.score >= self.quality_threshold:
                validation_result.issues = []
                validation_result.suggestions = []

            return validation_result

        except Exception as e:
            logger.error(f"Quality validation failed for {tool_name}: {e}")
            # Return default acceptable result to avoid blocking pipeline
            return ToolValidationResult(
                score=5.0,
                issues=[f"Quality validation failed: {str(e)}"],
                suggestions=["Manual review recommended"],
            )

    async def plan_retry_strategy(
        self, tool_name: str, validation_result: ToolValidationResult, state: VocabState
    ) -> RetryStrategy:
        """Determine retry strategy based on validation results."""

        retry_count = getattr(state, f"{tool_name}_retry_count", 0)

        # Don't retry if score is high enough
        if validation_result.score >= self.quality_threshold:
            return RetryStrategy(
                should_retry=False,
                retry_reason="Score meets quality threshold",
                adjusted_inputs={},
            )

        # On final retry, accept if score is above 6
        if retry_count >= self.max_retries:
            if validation_result.score >= 7.25:
                return RetryStrategy(
                    should_retry=False,
                    retry_reason="Final retry with acceptable score (>7.25)",
                    adjusted_inputs={},
                )
            else:
                return RetryStrategy(
                    should_retry=False,
                    retry_reason="Maximum retries reached",
                    adjusted_inputs={},
                )

        # Create quality feedback for supported tools
        adjusted_inputs = {}

        # Add quality feedback for tools that support it
        if tool_name in [
            "synonyms",
            "examples",
            "media",
            "translation",
            "validation",
            "classification",
            "syllables",
            "conjugation",
        ]:
            # Only include quality feedback if we have issues or suggestions
            if validation_result.issues or validation_result.suggestions:
                adjusted_inputs["quality_feedback"] = (
                    f"Quality score: {validation_result.score}/10. Please address the issues and follow the suggestions below."
                )
                adjusted_inputs["previous_issues"] = validation_result.issues
                adjusted_inputs["suggestions"] = validation_result.suggestions

        # Should retry if we haven't reached max retries and score is below threshold
        should_retry = (
            retry_count < self.max_retries
            and validation_result.score < self.quality_threshold
        )

        retry_reason = (
            f"Quality score {validation_result.score} below threshold {self.quality_threshold}"
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

        # Check if core sequential steps are complete with acceptable quality
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

        # Check if previous steps passed quality gates
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

        tasks = []

        # Always include these core tasks
        tasks.extend(["media", "examples", "synonyms", "syllables"])

        # Add conjugation only for verbs
        if getattr(state, "target_part_of_speech", None) == "verb":
            tasks.append("conjugation")

        # Pronunciation runs after syllables (no quality gate needed)
        tasks.append("pronunciation")

        return tasks


# Global supervisor instance
supervisor = VocabSupervisor()


def create_fallback_result(
    tool_name: str, inputs: dict[str, Any], error: str
) -> dict[str, Any]:
    """Create a fallback result when tool execution fails completely."""

    logger.error(f"Creating fallback result for {tool_name}: {error}")

    # Return appropriate fallback based on tool type
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
            "target_word": "ERROR - Translation tool failed: {error}",
            "target_part_of_speech": "verb",
            "target_article": None,
        },
        "media": {
            "media": {
                "url": "ERROR - Media tool failed: {error}",
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
            "phonetic_guide": "ERROR - Syllables tool failed: {error}",
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
