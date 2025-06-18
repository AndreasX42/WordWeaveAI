from typing import List, Optional

from langchain.tools import tool
from pydantic import BaseModel, Field
from vocab_processor.constants import Language
from vocab_processor.tools.base_tool import (
    SystemMessages,
    create_llm_response,
    create_tool_error_response,
)


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
        description="The detected language of the source word, if clear and unambiguous, otherwise null.",
    )
    message: Optional[str] = Field(
        None,
        description="An explanatory message if the word is not valid (e.g., 'Misspelled', 'Ambiguous language', 'Language not clear').",
    )
    suggestions: Optional[List[SuggestedWordInfo]] = Field(
        None,
        max_items=3,
        description="A list of suggested corrections or alternative words, including their language, if the input word is misspelled or ambiguous.",
    )


@tool
async def validate_word(word: str, target_language: Language) -> WordValidationResult:
    """
    Validates a word for spelling, language clarity, and ambiguity.

    - If the word is obviously a valid word in one of the supported languages
      (except the chosen target_language), return is_valid=True and source_language.
    - Otherwise, return is_valid=False, source_language=None, and up to 3 suggestions if possible.
    """

    possible_source_languages = [
        language for language in Language if language != target_language
    ]

    prompt = f"""You are an expert linguistic validator. For word '{word}' targeting {target_language}:

Instructions:
- Only suggest as correction a **real word** from the list of supported languages ({", ".join(possible_source_languages)}).
- If the input word is not valid, suggest up to 3 real, high-frequency words with the smallest possible spelling difference (edit distance up to 3). Only suggest corrections if they are common and actually exist in the language.
- **Never invent words.**
- **Never suggest rare words, names, or words in the target language.**
- **Never suggest the input word itself as a suggestion.**
- If the word is valid in any supported language (except the target language), mark as valid and return the detected language.
- Otherwise, return is_valid: false and suggestions as above.

Rules: No invented words, no rare words, no target language suggestions.
Supported: {", ".join(Language.all_values())}

Output JSON only."""

    try:
        return await create_llm_response(
            response_model=WordValidationResult,
            user_prompt=prompt,
            system_message=SystemMessages.VALIDATION_SPECIALIST,
            use_large_model=True,  # Use large model for validation accuracy
        )
    except Exception as e:
        # Create fallback error response
        return WordValidationResult(
            is_valid=False,
            source_language=None,
            message=f"An error occurred during validation: {str(e)}",
            suggestions=None,
        )
