from enum import Enum
from typing import Any

from aws_lambda_powertools import Logger
from pydantic import BaseModel, Field

from vocab_processor.constants import LLMVariant
from vocab_processor.tools.base_tool import SystemMessages, create_llm_response
from vocab_processor.tools.classification_tool import WordCategorization
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
    issues: list[str] = Field(default=[], description="List of identified issues")
    suggestions: list[str] = Field(default=[], description="Improvement suggestions")


class RetryStrategy(BaseModel):
    """Strategy for retrying failed tools."""

    should_retry: bool = Field(...)
    retry_reason: str = Field(...)
    adjusted_inputs: dict[str, Any] = Field(default={})
    use_stronger_model: bool = Field(default=False)


class LLMRouter:
    """Smart routing between expensive and cheap models."""

    @staticmethod
    def get_model_for_task(task_type: TaskType, is_retry: bool = False) -> LLMVariant:
        """Select appropriate LLM model based on task complexity."""

        # Use powerful model for supervisor decisions
        if task_type in [
            TaskType.SUPERVISION,
            TaskType.VALIDATION,
            TaskType.QUALITY_CHECK,
        ]:
            return LLMVariant.GPT41

        # Use cheaper model for routine tool execution, upgrade on retry
        if task_type in [
            TaskType.TRANSLATION,
            TaskType.EXAMPLES,
            TaskType.SYNONYMS,
            TaskType.SYLLABLES,
            TaskType.CONJUGATION,
            TaskType.MEDIA_SELECTION,
            TaskType.CLASSIFICATION,
        ]:
            return LLMVariant.GPT41 if is_retry else LLMVariant.GPT41M

        return LLMVariant.GPT41M


def get_schema_specification(model_class: BaseModel) -> str:
    """Extract schema specification from Pydantic model."""
    schema = model_class.model_json_schema()

    # Build a readable schema specification
    spec_lines = [f"**{model_class.__name__} Schema:**"]

    if "properties" in schema:
        for field_name, field_info in schema["properties"].items():
            field_type = field_info.get("type", "unknown")
            field_desc = field_info.get("description", "")

            # Handle array types
            if field_type == "array" and "items" in field_info:
                items_info = field_info["items"]
                if "$ref" in items_info:
                    # Extract referenced type name
                    ref_type = items_info["$ref"].split("/")[-1]
                    field_type = f"array of {ref_type}"
                else:
                    items_type = items_info.get("type", "unknown")
                    field_type = f"array of {items_type}"

            # Handle object types with $ref
            elif "$ref" in field_info:
                ref_type = field_info["$ref"].split("/")[-1]
                field_type = ref_type

            required = field_name in schema.get("required", [])
            req_text = "REQUIRED" if required else "optional"

            spec_lines.append(f"  - {field_name}: {field_type} ({req_text})")
            if field_desc:
                spec_lines.append(f"    Description: {field_desc}")

    # Add any additional constraints
    if "definitions" in schema:
        spec_lines.append("\n**Referenced Types:**")
        for def_name, def_info in schema["definitions"].items():
            spec_lines.append(f"  {def_name}:")
            if "properties" in def_info:
                for prop_name, prop_info in def_info["properties"].items():
                    prop_type = prop_info.get("type", "unknown")
                    prop_desc = prop_info.get("description", "")
                    spec_lines.append(f"    - {prop_name}: {prop_type}")
                    if prop_desc:
                        spec_lines.append(f"      {prop_desc}")

    return "\n".join(spec_lines)


class VocabSupervisor:
    """Supervisor for vocabulary processing quality control."""

    def __init__(self, quality_threshold: float = 7.0, max_retries: int = 2):
        self.quality_threshold = quality_threshold
        self.max_retries = max_retries
        self.router = LLMRouter()

        # Tools that should skip quality validation
        self.skip_validation_tools = {"pronunciation"}

        # Define expected schemas for each tool with actual Pydantic models
        self.tool_schemas = {
            "validation": WordValidationResult,
            "classification": WordCategorization,
            "translation": Translation,
            "examples": Examples,
            "synonyms": Synonyms,
            "syllables": SyllableBreakdown,
            "conjugation": ConjugationResult,
        }

    async def validate_tool_output(
        self, tool_name: str, result: Any, state: VocabState
    ) -> ToolValidationResult:
        """Schema-aware validation of tool outputs."""

        # Skip validation for tools that don't need it
        if tool_name in self.skip_validation_tools:
            return ToolValidationResult(score=10.0, issues=[], suggestions=[])

        # Get expected schema for the tool
        expected_schema_class = self.tool_schemas.get(tool_name)

        # Common context for all validations
        learning_context = f"""
        **VOCABULARY LEARNING CONTEXT:**
        This output is for a vocabulary learning application. The PRIMARY GOAL is to create 
        high-quality, natural content that helps language learners effectively acquire new words.
        
        **QUALITY STANDARDS:**
        - Content must feel natural and authentic in the target language
        - Information should be accurate and pedagogically sound
        - Examples and explanations should aid comprehension and retention
        - Cultural appropriateness and learner-friendliness are essential
        
        **LEARNER PERSPECTIVE:**
        Evaluate from the perspective of someone learning {state.target_language} who needs:
        - Clear, understandable explanations
        - Natural, commonly-used language
        - Practical, real-world examples
        - Culturally appropriate content
        """

        # Schema-specific validation prompts
        if tool_name == "validation":
            schema_spec = get_schema_specification(WordValidationResult)
            validation_prompt = f"""
            {learning_context}
            
            **TOOL: Word Validation**
            Validate this tool output against its expected Pydantic schema:
            
            {schema_spec}
            
            **Actual Result:**
            {result}
            
            **Context:**
            - Source word: "{state.source_word}"
            - Target language: {state.target_language}
            
            **VALIDATION TOOL PURPOSE:**
            This tool ONLY validates if input is a real word/phrase in ANY source language (not target).
            It should NOT provide translations, NOT suggest target language words, NOT flag phrases as problematic.
            
            **CORRECT BEHAVIOR:**
            - Input "to build" targeting Spanish → is_valid=True, source_language=English ✅
            - Input "la casa" targeting English → is_valid=True, source_language=Spanish ✅  
            - Input "blahblah" targeting any → is_valid=False, suggestions with real words ✅
            
            **VALIDATION CHECKLIST:**
            1. All required fields are present and have correct types
            2. is_valid is boolean (True/False)
            3. source_language is a valid Language enum value (like <Language.ENGLISH: 'English'>) or null
               - Enum values like <Language.ENGLISH: 'English'> are CORRECT and will serialize properly
            4. If suggestions exist, they are valid SuggestedWordInfo objects
            5. **CORRECT LOGIC:** 
               - If is_valid=True: input exists in a source language, source_language should be set
               - If is_valid=False: input is misspelled/invalid, should have message and/or suggestions
            6. Phrases like "to build" are VALID and should be accepted (not flagged as problematic)
            
            **LEARNING QUALITY CHECK:**
            - Does it correctly identify valid input as valid (including phrases)?
            - Does it correctly identify the source language?
            - Are spelling suggestions helpful for actually misspelled words?
            - Does it NOT try to do translation (which is another tool's job)?
            
            Rate 1-10 based on schema compliance, logical consistency, and validation accuracy.
            """

        elif tool_name == "translation":
            schema_spec = get_schema_specification(Translation)
            validation_prompt = f"""
            {learning_context}
            
            **TOOL: Translation**
            Validate this tool output against its expected Pydantic schema:
            
            {schema_spec}
            
            **Actual Result:**
            {result}
            
            **Context:**
            - Source: "{state.source_word}" ({state.source_language})
            - Target language: {state.target_language}
            
            **Validation Checklist:**
            1. All required fields are present and have correct types
            2. target_word is a reasonable translation
            3. target_part_of_speech is a valid PartOfSpeech enum value:
               - For English: "neuter noun" (not "noun" or "feminine noun")
               - For German: "masculine noun", "feminine noun", or "neuter noun"
               - For Spanish: "masculine noun" or "feminine noun"
               - Other: "verb", "adjective", "adverb", etc.
            4. target_article is appropriate for the language:
               - English: null (no gendered articles)
               - German: der/die/das for nouns
               - Spanish: el/la/los/las for nouns
            5. Translation accuracy and grammatical consistency
            
            **LEARNING QUALITY CHECK:**
            - Is this the most common, natural translation a learner should know?
            - Does the part of speech match how learners would use this word?
            - Are articles (if applicable) what learners would actually encounter?
            - Would this translation help learners communicate effectively?
            - **IMPORTANT**: For informal/slang source words, accuracy of register is MORE important than pedagogical politeness
            - If source word is vulgar/slang, vulgar translation may be MORE accurate than neutral ones
            - Does the translation help learners understand REAL usage in authentic contexts?
            
            Rate 1-10 based on schema compliance, translation accuracy, and learning effectiveness.
            Prioritize authenticity and register accuracy over pedagogical conservatism.
            """

        elif tool_name == "classification":
            schema_spec = get_schema_specification(WordCategorization)
            validation_prompt = f"""
            {learning_context}
            
            **TOOL: Word Classification**
            Validate this tool output against its expected Pydantic schema:
            
            {schema_spec}
            
            **Actual Result:**
            {result}
            
            **Context:**
            - Word: "{state.source_word}" ({state.source_language})
            
            **Validation Checklist:**
            1. All required fields are present and have correct types
            2. source_definition is a list of 1-3 strings
            3. source_part_of_speech is a valid PartOfSpeech enum value
            4. source_article is appropriate (string or null)
            5. Definitions are accurate and in the source language
            
            **LEARNING QUALITY CHECK:**
            - Are definitions clear and understandable for learners?
            - Do they represent the most common, essential meanings?
            - Is the part of speech classification pedagogically useful?
            - Are definitions written in natural, learner-friendly language?
            
            Rate 1-10 based on schema compliance, accuracy, and pedagogical value.
            """

        elif tool_name == "examples":
            schema_spec = get_schema_specification(Examples)
            validation_prompt = f"""
            {learning_context}
            
            **TOOL: Example Sentences**
            Validate this tool output against its expected Pydantic schema:
            
            {schema_spec}
            
            **Actual Result:**
            {result}
            
            **Context:**
            - Source word: "{state.source_word}" ({state.source_language})
            - Target word: "{state.target_word}" ({state.target_language})
            
            **Validation Checklist:**
            1. All required fields are present and have correct types
            2. examples list has 3-4 items (within min/max constraints)
            3. Each example has 'original' (min 20 chars) and 'translation' (min 30 chars)
            4. Examples use the words correctly in context
            5. Translations are accurate and natural
            6. Context field (if present) is helpful
            
            **LEARNING QUALITY CHECK:**
            - Are examples practical and likely to be encountered in real life?
            - Do they demonstrate natural, common usage of the word?
            - Are translations smooth and idiomatic in the target language?
            - Do examples help learners understand when/how to use the word?
            - Are contexts culturally appropriate and learner-friendly?
            
            Rate 1-10 based on schema compliance, naturalness, and learning effectiveness.
            """

        elif tool_name == "synonyms":
            schema_spec = get_schema_specification(Synonyms)
            validation_prompt = f"""
            {learning_context}
            
            **TOOL: Synonyms**
            Validate this tool output against its expected Pydantic schema:
            
            {schema_spec}
            
            **Actual Result:**
            {result}
            
            **Context:**
            - Target word: "{state.target_word}" ({state.target_language})
            - Part of speech: {state.target_part_of_speech}
            
            **Validation Checklist:**
            1. All required fields are present and have correct types
            2. synonyms list contains Synonym objects
            3. Each synonym has both 'synonym' and 'explanation' fields
            4. Synonyms are actually synonymous with the target word
            5. Explanations are helpful and in target language
            6. Synonyms match the correct part of speech
            
            **LEARNING QUALITY CHECK:**
            - Are synonyms commonly used words for the target word {state.target_word} in the target language {state.target_language}?
            - Do explanations help learners understand subtle differences?
            - Are explanations written in clear, natural language?
            
            Rate 1-10 based on schema compliance, synonym quality, and learning value.
            """

        elif tool_name == "syllables":
            schema_spec = get_schema_specification(SyllableBreakdown)
            validation_prompt = f"""
            {learning_context}
            
            **TOOL: Syllable Breakdown**
            Validate this tool output against its expected Pydantic schema:
            
            {schema_spec}
            
            **Actual Result:**
            {result}
            
            **Context:**
            - Target word: "{state.target_word}" ({state.target_language})
            
            **Validation Checklist:**
            1. All required fields are present and have correct types
            2. syllables is a list of strings
            3. phonetic_guide is a string with pronunciation information
            4. Syllable breakdown is accurate for the word
            5. Phonetic guide is helpful and correct (IPA or common symbols)
            
            **LEARNING QUALITY CHECK:**
            - Does the syllable breakdown help learners pronounce the word correctly?
            - Is the phonetic guide accessible and useful for language learners?
            - Are syllables divided in a way that aids pronunciation learning?
            - Would this help learners develop better pronunciation skills?
            
            Rate 1-10 based on schema compliance, accuracy, and pronunciation learning value.
            """

        elif tool_name == "conjugation":
            schema_spec = get_schema_specification(ConjugationResult)
            validation_prompt = f"""
            {learning_context}
            
            **TOOL: Verb Conjugation**
            Validate this tool output against its expected Pydantic schema:
            
            {schema_spec}
            
            **Actual Result:**
            {result}
            
            **Context:**
            - Target word: "{state.target_word}" ({state.target_language})
            - Part of speech: {state.target_part_of_speech}
            
            **Validation Checklist:**
            1. All required fields are present and have correct types
            2. conjugation field is a valid JSON string
            3. JSON contains proper conjugation structure for the language
            4. Conjugations are accurate for the verb
            5. All required verb forms are present
            6. Language-specific conjugation patterns are correct
            
            **LEARNING QUALITY CHECK:**
            - Are conjugations the most common, essential forms learners need?
            - Do conjugations follow natural, standard patterns?
            - Are all forms grammatically correct and commonly used?
            - Would this conjugation table help learners use the verb correctly?
            - Are irregular forms properly indicated?
            
            Rate 1-10 based on schema compliance, conjugation accuracy, and learning utility.
            """

        elif tool_name == "media":
            validation_prompt = f"""
            {learning_context}
            
            **TOOL: Visual Media**
            Validate this Media tool output focusing on search query quality:
            
            **Actual Result:**
            {result}
            
            **Context:**
            - Target word: "{state.target_word}" ({state.target_language})
            
            **Expected Structure:**
            - media: Media object with url, alt, src, explanation, memory_tip
            - english_word: string
            - search_query: list of descriptive English terms
            - media_reused: boolean
            
            **Validation Focus (Search Query Quality):**
            1. Does the search_query contain descriptive English terms?
            2. Are search terms specific and likely to return relevant photos?
            3. Would these terms help find good visual representations of the word?
            4. Are the terms clear and unambiguous?
            5. Basic structure compliance (media object present, etc.)
            
            **LEARNING QUALITY CHECK:**
            - Would the search terms lead to images that help learners understand the word?
            - Are search terms culturally appropriate and learner-friendly?
            - Do terms avoid ambiguity that might confuse visual learning?
            - Would resulting images aid vocabulary retention and recall?
            
            I trust the photo selection process - focus on search query reasonableness and learning value.
            Rate 1-10 based primarily on search query quality, learning effectiveness, and structure.
            """

        else:
            # Generic schema validation for unknown tools
            validation_prompt = f"""
            {learning_context}
            
            Tool: {tool_name}
            Validate output format and quality:
            
            Result:
            {result}
            
            Context:
            - Source: {state.source_word} ({state.source_language})
            - Target: {state.target_word} ({state.target_language})
            
            Check:
            1. Valid structure
            2. Required fields present
            3. Correct data types
            4. Content relevance
            
            Learning value:
            - Effective for vocabulary learning?
            - Natural for learners?
            
            Rate 1-10 on quality and learning value.
            If score >= 8, return score only without issues/suggestions.
            If score < 8, include specific issues and improvement suggestions.
            """

        try:
            validation_result = await create_llm_response(
                response_model=ToolValidationResult,
                user_prompt=validation_prompt,
                system_message=SystemMessages.VALIDATION_SPECIALIST,
                llm_provider=self.router.get_model_for_task(TaskType.QUALITY_CHECK),
            )

            # For high scores, clear issues and suggestions
            if validation_result.score >= 8.0:
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
        if validation_result.score >= 8.0:
            return RetryStrategy(
                should_retry=False,
                retry_reason="Score meets quality threshold",
                adjusted_inputs={},
                use_stronger_model=False,
            )

        if retry_count >= self.max_retries:
            return RetryStrategy(
                should_retry=False,
                retry_reason="Maximum retries reached",
                adjusted_inputs={},
                use_stronger_model=False,
            )

        # Create quality feedback for supported tools
        adjusted_inputs = {}

        # Add quality feedback for tools that support it
        if tool_name in [
            "synonyms",
            "examples",
            "media",
            "translation",
            "classification",
            "syllables",
            "conjugation",
        ]:
            # Only include quality feedback if we have issues
            if validation_result.issues:
                adjusted_inputs["quality_feedback"] = (
                    f"Quality score: {validation_result.score}/10. Issues: {'; '.join(validation_result.issues)}"
                )
                adjusted_inputs["previous_issues"] = validation_result.issues

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
            use_stronger_model=retry_count > 0,
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
            "error_message": f"Validation failed: {error}",
            "suggestions": [],
        },
        "classification": {
            "source_word": inputs.get("source_word", "word"),
            "source_definition": ["Definition unavailable"],
            "source_part_of_speech": "verb",
            "source_article": None,
        },
        "translation": {
            "target_word": "translation unavailable",
            "target_part_of_speech": "verb",  # Default to verb for fallback
            "target_article": None,
        },
        "media": {
            "media": {
                "url": "",
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
                }
            ]
        },
        "synonyms": {"synonyms": []},
        "syllables": {
            "syllables": [inputs.get("target_word", "word")],
            "phonetic_guide": "",
        },
        "pronunciation": {"pronunciations": ""},
        "conjugation": {"conjugation": None},
    }

    return fallback_results.get(
        tool_name, {"error": f"Tool {tool_name} failed: {error}"}
    )
