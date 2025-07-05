from typing import List, Optional

from langchain.tools import tool
from pydantic import BaseModel, Field

from vocab_processor.constants import Language
from vocab_processor.tools.base_tool import (
    add_quality_feedback_to_prompt,
    create_llm_response,
)


class SyllableBreakdown(BaseModel):
    """Syllable breakdown of the word in the specified language."""

    syllables: List[str] = Field(..., description="List of syllables for the word")
    phonetic_guide: str = Field(..., description="Phonetic pronunciation guide")


@tool
async def get_syllables(
    target_word: str,
    target_language: Language,
    quality_feedback: Optional[str] = None,
    previous_issues: Optional[List[str]] = None,
) -> SyllableBreakdown:
    """Break down a word into syllables with phonetic guidance."""

    # Base prompt
    prompt = f"Break '{target_word}' ({target_language}) into syllables. Provide syllable list and clear phonetic guide (IPA or learner-friendly symbols)."

    # Quality requirements for syllables
    quality_requirements = [
        "Syllable breakdown helps learners pronounce the word correctly",
        "Phonetic guide is accessible and useful for language learners",
        "Syllables are divided naturally for pronunciation learning",
        "Use clear, learner-friendly phonetic notation",
        "Guide should help learners develop better pronunciation skills",
        f"Consider stress patterns and intonation if relevant for {target_language}",
    ]

    # Add quality feedback if provided
    enhanced_prompt = add_quality_feedback_to_prompt(
        prompt, quality_feedback, previous_issues, quality_requirements
    )

    return await create_llm_response(
        response_model=SyllableBreakdown,
        user_prompt=enhanced_prompt,
    )
