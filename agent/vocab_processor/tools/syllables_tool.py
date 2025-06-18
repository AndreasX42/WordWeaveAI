from typing import List

from langchain.tools import tool
from pydantic import BaseModel, Field
from vocab_processor.constants import Language
from vocab_processor.tools.base_tool import create_llm_response


class SyllableBreakdown(BaseModel):
    """Syllable breakdown of the word in the specified language."""

    syllables: List[str] = Field(..., description="List of syllables for the word")
    phonetic_guide: str = Field(..., description="Phonetic pronunciation guide")


@tool
async def get_syllables(
    target_word: str, target_language: Language
) -> SyllableBreakdown:
    """Break down a word into syllables with phonetic guidance."""

    prompt = f"Break '{target_word}' ({target_language}) into syllables. Provide syllable list and phonetic guide (IPA or common symbols)."

    return await create_llm_response(
        response_model=SyllableBreakdown,
        user_prompt=prompt,
    )
