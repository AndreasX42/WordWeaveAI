from langchain_core.tools import tool
from pydantic import BaseModel, Field
from typing import List, Optional

from my_agent.constants import instructor_llm, Language

class SuggestedWordInfo(BaseModel):
    word: str = Field(..., description="The suggested word string.")
    language: Language = Field(..., description="The language of the suggested word.")

class WordValidationResult(BaseModel):
    is_valid: bool = Field(..., description="True if the word is considered valid (correctly spelled, unambiguous language), False otherwise.")
    source_language: Optional[Language] = Field(None, description="The detected language of the source word if clear and unambiguous, otherwise null.")
    message: Optional[str] = Field(None, description="An explanatory message if the word is not valid (e.g., 'Misspelled', 'Ambiguous language', 'Language not clear').")
    suggestions: Optional[List[SuggestedWordInfo]] = Field(None, max_items=3, description="A list of suggested corrections or alternative words, including their language, if the input word is misspelled or ambiguous.")

@tool
async def validate_word(word: str, target_language: Language) -> WordValidationResult:
    """
    Validates a word for spelling, language clarity, and ambiguity.

    - If the word is obviously a valid word in one of the supported languages
      (except the chosen target_language), return is_valid=True and source_language.
    - Otherwise, return is_valid=False, source_language=None, and up to 3 suggestions if possible.
    """

    possible_source_languages = [language for language in Language if language != target_language]

    system_prompt = f"""
You are a strict, expert linguistic validation assistant.

Instructions:
- Only suggest as correction a **real word** from the list of supported languages ({", ".join(possible_source_languages)}).
- If the input word is not valid, suggest up to 3 real, high-frequency words with the smallest possible spelling difference (edit distance of 1 or 2). Only suggest corrections if they are common and actually exist in the language.
- **Never invent words.**
- **Never suggest rare words, names, or words in the target language.**
- **Never suggest the input word itself as a suggestion.**
- If the word is valid in any supported language (except the target language), mark as valid and return the detected language.
- Otherwise, return is_valid: false and suggestions as above.

Examples:
- Word: "Haus" (German), Target: Spanish → is_valid: true, source_language: "German"
- Word: "naughty" (English), Target: German → is_valid: true, source_language: "English"
- Word: "quisquilloso" (Spanish), Target: German → is_valid: true, source_language: "Spanish"
- Word: "maus" (misspelled), Target: English → is_valid: false, source_language: null, message: "Misspelled", suggestions: [{{"word": "Haus", "language": "German"}}, {{"word": "Maus", "language": "German"}}]
- Word: "mekern" (misspelled), Target: Spanish → is_valid: false, source_language: null, message: "Misspelled", suggestions: [{{"word": "meckern", "language": "German"}}, {{"word": "merken", "language": "German"}}]
- Word: "conducer" (misspelled), Target: English → is_valid: false, source_language: null, message: "Misspelled", suggestions: [{{"word": "conducir", "language": "Spanish"}}]

Supported languages: {", ".join(Language.all_values())}.
Strictly return a JSON object with these keys only:
- is_valid (bool)
- source_language (Language|null)
- message (str|null)
- suggestions (list|null, each item: {{'word': str, 'language': Language}})

Output only the JSON, no commentary or explanations.
"""

    user_prompt = (
        f"Validate the word: '{word}' for target language '{target_language}'."
    )
    try:
        response = await instructor_llm.create(
            response_model=WordValidationResult,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
        )
        return response
    except Exception as e:
        return WordValidationResult(
            is_valid=False,
            source_language=None,
            message=f"An error occurred during validation: {str(e)}",
            suggestions=None
        )