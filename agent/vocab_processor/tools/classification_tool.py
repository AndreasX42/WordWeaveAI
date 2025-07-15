from typing import Optional

from langchain.tools import tool
from pydantic import BaseModel, Field

from vocab_processor.constants import Language, PartOfSpeech
from vocab_processor.tools.base_tool import (
    add_quality_feedback_to_prompt,
    create_llm_response,
)
from vocab_processor.utils.ddb_utils import check_word_exists, lang_code


class WordCategorization(BaseModel):
    """Categorization of the word in the specified language."""

    source_word: str = Field(
        ...,
        description="The source source word to categorize, without any article or additional information",
    )

    source_definition: list[str] = Field(
        ...,
        min_items=1,
        max_items=3,
        description="Definition of the source word in its source language",
    )
    source_part_of_speech: PartOfSpeech = Field(
        ..., description="Part of speech of the source word"
    )
    source_article: str | None = Field(
        None,
        description="Article of the source word in the source language, if it is a noun.",
    )
    source_additional_info: str | None = Field(
        None,
        description="Additional information in the source language about the word in the source language if needed. For example if the word is only common in a specific country or region, in what context the word is used, if it is colloquial or vulgar, etc.",
    )

    # Add existence check fields
    word_exists: Optional[bool] = Field(
        None,
        description="Whether the word already exists in the database",
    )
    existing_item: Optional[dict] = Field(
        None,
        description="The existing database item if the word already exists",
    )


@tool
async def get_classification(
    source_word: str,
    source_language: Language,
    target_language: Language,
    quality_feedback: Optional[str] = None,
    previous_issues: Optional[list[str]] = None,
    suggestions: Optional[list[str]] = None,
) -> WordCategorization:
    """Categorize part of speech and language, then check if word exists in database."""

    # Base prompt
    prompt = f"""Classify '{source_word}' ({source_language}): part of speech ({', '.join(PartOfSpeech.all_values())}). 
    
    Extract the base form of the word, removing any articles or modifiers.
    
    For source_article:
    - English: null (no articles needed)
    - German: der/die/das for nouns
    - Spanish: el/la/los/las for nouns
    """

    # Quality requirements for classification
    quality_requirements = [
        "Extract base word correctly, removing any articles or modifiers",
        f"1-3 clear and natural {source_language.value} definitions that are distinct and common",
        f"Note informal/slang usage and other important information in source_additional_info in {source_language}",
    ]

    # Add quality feedback if provided
    enhanced_prompt = add_quality_feedback_to_prompt(
        prompt, quality_feedback, previous_issues, suggestions, quality_requirements
    )

    # Get the classification first
    classification = await create_llm_response(
        response_model=WordCategorization,
        user_prompt=enhanced_prompt,
    )

    # After getting the base word, check if it exists in the database
    existence_check = await check_word_exists(
        base_word=classification.source_word,
        source_language=source_language,
        target_language=lang_code(target_language),
        source_part_of_speech=classification.source_part_of_speech,
    )

    # Add existence check results to the classification
    classification.word_exists = existence_check["exists"]
    classification.existing_item = existence_check["existing_item"]

    return classification
