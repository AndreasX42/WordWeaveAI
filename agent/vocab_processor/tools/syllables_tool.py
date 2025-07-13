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

    syllables: List[str] = Field(
        ..., description="List of syllables for the target word"
    )
    phonetic_guide: str = Field(
        ...,
        description="Phonetic pronunciation guide (IPA) in the target language of the target word.",
    )


@tool
async def get_syllables(
    target_word: str,
    target_language: Language,
    quality_feedback: Optional[str] = None,
    previous_issues: Optional[List[str]] = None,
    suggestions: Optional[List[str]] = None,
) -> SyllableBreakdown:
    """Break down a word into syllables with phonetic guidance."""

    # Base prompt
    prompt = f"""Break '{target_word}' ({target_language}) into syllables. Provide a syllable list and a clear phonetic guide using the International Phonetic Alphabet (IPA).

**IMPORTANT RULES for {target_language}:**
- For Spanish verbs ending in '-ear', the 'e' and 'a' are in SEPARATE syllables, creating a hiatus.
- For Spanish verbs ending in '-uir', the 'ui' is a diphthong and stays in one syllable.
- The IPA guide MUST be accurate and use standard symbols.

Provide the breakdown for: '{target_word}'"""

    # Quality requirements for syllables
    quality_requirements = [
        f"Syllables must be correct for the target word {target_word} in {target_language}, following the rules provided, taking into account the possible original source language nuances.",
        "Phonetic guide must be accurate and in the International Phonetic Alphabet (IPA).",
    ]

    # Add quality feedback if provided
    enhanced_prompt = add_quality_feedback_to_prompt(
        prompt, quality_feedback, previous_issues, suggestions, quality_requirements
    )

    return await create_llm_response(
        response_model=SyllableBreakdown,
        user_prompt=enhanced_prompt,
    )
