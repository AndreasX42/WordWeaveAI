from typing import Optional

from langchain.tools import tool
from pydantic import BaseModel, Field

from vocab_processor.constants import Language
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
    message: Optional[str] = Field(
        None,
        description="An explanatory message if the word is not valid (e.g., 'Misspelled', 'Ambiguous language', 'Language not clear').",
    )
    suggestions: Optional[list[SuggestedWordInfo]] = Field(
        None,
        max_items=3,
        description="A list of suggested corrections or alternative words, including their language, if the input word is misspelled or ambiguous.",
    )


def _build_validation_prompt(
    word: str, target_language: Language, source_language: Optional[Language] = None
) -> str:
    """Build the validation prompt with clear instructions."""

    if source_language is None:
        possible_source_languages = [
            language for language in Language if language != target_language
        ]
    else:
        possible_source_languages = [source_language]

    return f"""You are an expert linguistic validator. For input '{word}' of source language (if provided) '{source_language if source_language else ""}', with the aim to translate it to {target_language}:

Instructions:
- Keep the source_word exactly as provided by the user (preserve "to build", "la casa", etc.)
- Validate if the input is a valid word/phrase in any supported and possible source language {possible_source_languages}
- If the source_language is provided, validate if the input is a valid word/phrase in the source language
- Accept common articles, prefixes and modifiers (like "to", "la", "el", "der", "die", "das", "the") as part of valid input
- If the input is valid in any supported and possible source language {possible_source_languages}, mark as valid and return the detected language
- If the input is not valid/misspelled, suggest up to 3 real, high-frequency corrections with smallest spelling difference (edit distance up to 3)
- Only suggest corrections if they are common and actually exist in the possible source languages {possible_source_languages}
- **Never invent words.**
- **Never suggest rare words, names, or words in the target language.**
- **Never suggest the input word itself as a suggestion.**

Rules: No invented words, no rare words, no target language suggestions.
Supported: {", ".join(Language.all_values())}

Output JSON only."""


@tool
async def validate_word(
    source_word: str,
    target_language: Language,
    source_language: Optional[Language] = None,
) -> WordValidationResult:
    """Validates a word for spelling, language clarity, and ambiguity."""

    prompt = _build_validation_prompt(source_word, target_language, source_language)

    try:
        return await create_llm_response(
            response_model=WordValidationResult,
            user_prompt=prompt,
            system_message=SystemMessages.VALIDATION_SPECIALIST,
        )
    except Exception as e:
        return WordValidationResult(
            is_valid=False,
            source_language=None,
            message=f"An error occurred during validation: {str(e)}",
            suggestions=None,
        )
