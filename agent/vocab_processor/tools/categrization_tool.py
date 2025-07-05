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
        description="Additional information about the word in the source language if needed. For example if the word is only common in a specific country or region, in what context the word is used, if it is colloquial or vulgar, etc.",
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
    prompt = f"Classify '{source_word}' ({source_language}): provide part of speech from {', '.join(PartOfSpeech.all_values())} and up to 2 clear definitions in {source_language}. If the word is a noun, provide the article. Also provide the base word in the source_word field, for example if the input is 'to build', the source_word should be 'build'."

    # Quality requirements for classification
    quality_requirements = [
        "Correctly extract the base word from inputs with articles/prefixes (to build → build, la casa → casa)",
        "Return the extracted base word in the source_word field (not the original input)",
        f"Provide exactly 1-2 definitions maximum - NEVER exceed 2 definitions",
        f"Definitions are clear, accurate, and natural for native {source_language} speakers",
        "Each definition must represent a DISTINCTLY DIFFERENT meaning or usage context - avoid repetitive synonyms",
        "For basic words with one main meaning, provide only ONE definition rather than multiple similar ones",
        "Provide the most common, essential meanings (not obscure ones)",
        "Part of speech should be pedagogically useful",
        "If the word is informal/slang, make this clear in the definitions",
        f"Include appropriate articles for nouns in {source_language}",
        "Do not create artificial variations of the same concept",
    ]

    # Add quality feedback if provided
    enhanced_prompt = add_quality_feedback_to_prompt(
        prompt, quality_feedback, previous_issues, quality_requirements
    )

    return await create_llm_response(
        response_model=WordCategorization,
        user_prompt=enhanced_prompt,
    )
