from typing import Optional

from langchain.tools import tool
from pydantic import BaseModel, Field

from vocab_processor.constants import Language, PartOfSpeech
from vocab_processor.tools.base_tool import (
    add_quality_feedback_to_prompt,
    create_llm_response,
)


class Synonym(BaseModel):
    """Synonyms of the word in the specified language."""

    synonym: str = Field(
        ..., description="Commonly used synonym of the word in the target language"
    )
    explanation: str = Field(
        ..., description="Explanation of the synonym in the source language"
    )


class Synonyms(BaseModel):
    """List of synonyms in the target language."""

    note: Optional[str] = Field(
        None,
        description="Note in the source language about the synonyms, for example, if no direct synonym exists.",
    )
    synonyms: list[Synonym] = Field(
        ...,
        description="List of synonyms of the target word in the target language",
        min_items=1,
        max_items=3,
    )


@tool
async def get_synonyms(
    target_word: str,
    source_language: Language,
    target_language: Language,
    target_part_of_speech: PartOfSpeech,
    quality_feedback: Optional[str] = None,
    previous_issues: Optional[list[str]] = None,
    suggestions: Optional[list[str]] = None,
) -> Synonyms:
    """Return synonyms of the word in the specified language."""

    # Base prompt
    prompt = f"""You are a linguistic expert providing synonyms for '{target_word}' ({target_language}, {target_part_of_speech}).

**Analysis and Instructions:**
1.  First, determine if direct, common synonyms for '{target_word}' exist in {target_language}.
2.  If no direct synonyms exist, you must add a note in the source language {source_language} to briefly explain why no direct synonym exists.
3.  In any case, provide at least 1 to a maximum 3 of the closest words or concepts.
4.  For each synonym, the explanation should be in the source language {source_language} and clarify the nuances and differences of the synonym compared to '{target_word}'.

**Input Word:** '{target_word}'
"""

    # Quality requirements for synonyms
    quality_requirements = [
        "If no direct synonym exists, this must be stated in the 'note' field.",
        "The `synonyms` list should contain the closest related concepts, not meta-commentary.",
        "If the synonym is very uncommon but valid, it should be noted in explanation.",
        f"Explanations must clarify subtle differences in meaning and usage in the source language {source_language}.",
        "Try to avoid archaic or overly academic terms unless the source word is also of that nature.",
    ]

    # Add quality feedback if provided
    enhanced_prompt = add_quality_feedback_to_prompt(
        prompt, quality_feedback, previous_issues, suggestions, quality_requirements
    )

    return await create_llm_response(
        response_model=Synonyms,
        user_prompt=enhanced_prompt,
    )
