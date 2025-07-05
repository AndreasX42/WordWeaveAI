from typing import List, Optional

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
    explanation: str = Field(..., description="Explanation of the synonym")


class Synonyms(BaseModel):
    synonyms: list[Synonym] = Field(
        ...,
        description="List of synonyms in the original language",
        min_items=1,
        max_items=3,
    )


@tool
async def get_synonyms(
    target_word: str,
    target_language: Language,
    target_part_of_speech: PartOfSpeech,
    quality_feedback: Optional[str] = None,
    previous_issues: Optional[List[str]] = None,
) -> Synonyms:
    """Return synonyms of the word in the specified language."""

    # Base prompt
    prompt = f"Provide common {target_part_of_speech} synonyms for '{target_word}' in {target_language}. Include explanations in {target_language}."

    # Quality requirements for synonyms
    quality_requirements = [
        f"All synonyms are actual {target_part_of_speech} (not nouns if looking for verbs, etc.)",
        "Synonyms are direct and accurate translations/equivalents",
        "Avoid overly specific or contextual terms unless they're commonly used",
        "Include the most common and direct synonyms first",
        "Explanations should clarify proper usage and context",
    ]

    # Add quality feedback if provided
    enhanced_prompt = add_quality_feedback_to_prompt(
        prompt, quality_feedback, previous_issues, quality_requirements
    )

    return await create_llm_response(
        response_model=Synonyms,
        user_prompt=enhanced_prompt,
    )
