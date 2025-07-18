from typing import Optional

from langchain_core.tools import tool
from pydantic import BaseModel, Field

from vocab_processor.constants import Language
from vocab_processor.prompts_simple import VALIDATION_PROMPT_TEMPLATE
from vocab_processor.tools.base_tool import SystemMessages, create_llm_response


class SuggestedWordInfo(BaseModel):
    """Suggested word information."""

    word: str = Field(..., description="The suggested word.")
    language: Language = Field(..., description="The language of the suggested word.")


class WordValidationResult(BaseModel):
    """Validation result of the word."""

    is_valid: bool = Field(
        ...,
        description="True if the word is considered valid, False otherwise.",
    )
    source_language: Optional[Language] = Field(
        None,
        description="The language of the source word. Will be either provided by the user or detected by the validation assistant.",
    )
    issue_message: Optional[str] = Field(
        None,
        description="Only in case of invalid word: Explanation for why the word is not valid.",
    )
    issue_suggestions: Optional[list[SuggestedWordInfo]] = Field(
        None,
        max_length=3,
        description="Only in case of invalid word: A list of suggestions for the invalid word.",
    )


class ValidationResponse(BaseModel):
    result: WordValidationResult
    prompt: str


@tool
async def validate_word(
    source_word: str,
    target_language: Language,
    source_language: Optional[Language] = None,
    quality_feedback: Optional[str] = None,
    previous_issues: Optional[list[str]] = None,
    suggestions: Optional[list[str]] = None,
) -> ValidationResponse:
    """Validates a word for spelling, language clarity, and ambiguity."""

    if source_language is None:
        possible_source_languages = [
            language for language in Language if language != target_language
        ]
    else:
        possible_source_languages = [source_language]

    prompt = VALIDATION_PROMPT_TEMPLATE.build_enhanced_prompt(
        source_word=source_word,
        source_language=source_language.value if source_language else "unknown",
        possible_source_languages=", ".join(l.value for l in possible_source_languages),
        quality_feedback=quality_feedback,
        previous_issues=previous_issues,
        suggestions=suggestions,
    )

    try:
        result = await create_llm_response(
            response_model=WordValidationResult,
            user_prompt=prompt,
            system_message=SystemMessages.VALIDATION_SPECIALIST,
        )

        return ValidationResponse(result=result, prompt=prompt)
    except Exception as e:
        result = WordValidationResult(
            is_valid=False,
            source_language=None,
            issue_message=f"An error occurred during validation: {str(e)}",
            issue_suggestions=None,
        )
        return ValidationResponse(result=result, prompt=prompt)
