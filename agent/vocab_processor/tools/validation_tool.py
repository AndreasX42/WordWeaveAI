from typing import Optional

from langchain.tools import tool
from pydantic import BaseModel, Field

from vocab_processor.constants import Language
from vocab_processor.prompts import VALIDATION_PROMPT_TEMPLATE
from vocab_processor.tools.base_tool import SystemMessages, create_llm_response


class SuggestedWordInfo(BaseModel):
    """Suggested word information."""

    word: str = Field(..., description="The suggested word string.")
    language: Language = Field(..., description="The language of the suggested word.")


class WordValidationResult(BaseModel):
    """Validation result of the word."""

    is_valid: bool = Field(
        ...,
        description="True if the word is considered valid (correctly spelled, unambiguous language), False otherwise.",
    )
    source_language: Optional[Language] = Field(
        None,
        description="The language of the source word. Will be either provided by the user or detected by the validation step. Has to be a clear, unambiguous and supported language.",
    )
    issue_message: Optional[str] = Field(
        None,
        description="An explanatory message if the word is not valid (e.g., 'Misspelled', 'Ambiguous language', 'Language not clear').",
    )
    issue_suggestions: Optional[list[SuggestedWordInfo]] = Field(
        None,
        max_items=3,
        description="A list of suggested corrections or alternative words, including their language, if the input word is misspelled or ambiguous.",
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
        word=source_word,
        target_language=target_language.value,
        source_language=source_language.value if source_language else "",
        possible_source_languages=", ".join(l.value for l in possible_source_languages),
        all_languages=", ".join(Language.all_values()),
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
