from typing import Optional

from langchain.tools import tool
from pydantic import BaseModel, Field

from vocab_processor.constants import Language, PartOfSpeech
from vocab_processor.prompts import CLASSIFICATION_PROMPT_TEMPLATE
from vocab_processor.tools.base_tool import create_llm_response
from vocab_processor.utils.ddb_utils import check_word_exists, lang_code


class WordClassification(BaseModel):
    """Categorization of the word in the specified language."""

    source_word: str = Field(
        ...,
        description="The source source word to categorize, without any article or additional information",
    )

    source_definition: list[str] = Field(
        ...,
        min_length=1,
        max_length=3,
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
        description="Information about very important or special context, informal/slang usage, meaning and regional usage of the source word in its language",
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


class ClassificationResponse(BaseModel):
    result: WordClassification
    prompt: str


@tool
async def get_classification(
    source_word: str,
    source_language: Language,
    target_language: Language,
    quality_feedback: Optional[str] = None,
    previous_issues: Optional[list[str]] = None,
    suggestions: Optional[list[str]] = None,
) -> ClassificationResponse:
    """Categorize part of speech and language, then check if word exists in database."""

    enhanced_prompt = CLASSIFICATION_PROMPT_TEMPLATE.build_enhanced_prompt(
        quality_feedback=quality_feedback,
        previous_issues=previous_issues,
        suggestions=suggestions,
        source_word=source_word,
        source_language=source_language.value,
        part_of_speech_values=", ".join(PartOfSpeech.all_values()),
    )

    # Get the classification first
    classification = await create_llm_response(
        response_model=WordClassification,
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

    return ClassificationResponse(result=classification, prompt=enhanced_prompt)
