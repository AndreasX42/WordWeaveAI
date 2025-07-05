from typing import List, Optional

from langchain.tools import tool
from pydantic import BaseModel, Field

from vocab_processor.constants import Language, PartOfSpeech
from vocab_processor.tools.base_tool import (
    add_quality_feedback_to_prompt,
    create_llm_response,
)


class WordCategorization(BaseModel):
    """Categorization of the word in the specified language."""

    source_word: str = Field(
        ...,
        description="The base source word to categorize, without any article or additional information",
    )

    source_definition: list[str] = Field(
        ...,
        min_items=1,
        max_items=2,
        description="Definition of the word in its native language",
    )
    source_part_of_speech: PartOfSpeech = Field(
        ..., description="Part of speech of the source word"
    )
    source_article: str | None = Field(
        None,
        description="Article of the source word in the source language, if it is a noun",
    )
    source_additional_info: str | None = Field(
        None,
        description="Additional information in the source language about the word in the source language if needed. For example if the word is only common in a specific country or region, in what context the word is used, if it is colloquial or vulgar, etc.",
    )


@tool
async def get_classification(
    source_word: str,
    source_language: Language,
    quality_feedback: Optional[str] = None,
    previous_issues: Optional[List[str]] = None,
) -> WordCategorization:
    """Categorize part of speech and language."""

    # Base prompt
    prompt = f"Classify '{source_word}' ({source_language}): part of speech ({', '.join(PartOfSpeech.all_values())}), 1-2 {source_language} definitions. For nouns: add article. For inputs like 'to build' or 'la casa', extract base word (build, casa)."

    # Quality requirements for classification
    quality_requirements = [
        "Extract base word correctly (to build → build)",
        "Return base word in source_word field",
        "1-2 definitions max - distinct meanings only",
        f"Clear, natural {source_language} definitions",
        "Most common meanings only",
        "Pedagogically useful part of speech",
        f"Include articles for {source_language} nouns",
        f"Note informal/slang usage and other important information in source_additional_info in {source_language}",
    ]

    # Add quality feedback if provided
    enhanced_prompt = add_quality_feedback_to_prompt(
        prompt, quality_feedback, previous_issues, quality_requirements
    )

    return await create_llm_response(
        response_model=WordCategorization,
        user_prompt=enhanced_prompt,
    )
