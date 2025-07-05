from typing import List, Optional

from langchain.tools import tool
from pydantic import BaseModel, Field

from vocab_processor.constants import Language
from vocab_processor.tools.base_tool import (
    add_quality_feedback_to_prompt,
    create_llm_response,
)


class ExampleSentence(BaseModel):
    """A bilingual example sentence with translation."""

    original: str = Field(
        ..., description="The example sentence in the source language", min_length=20
    )
    translation: str = Field(
        ...,
        description="The translation of the example sentence into the target language",
        min_length=30,
    )
    context: Optional[str] = Field(
        None,
        description="Optional context or usage note for the example in the source language",
    )


class Examples(BaseModel):
    examples: list[ExampleSentence] = Field(
        ...,
        description="List of example sentences using the word and its translation.",
        min_items=3,
        max_items=4,
    )


@tool
async def get_examples(
    source_word: str,
    target_word: str,
    source_language: Language,
    target_language: Language,
    quality_feedback: Optional[str] = None,
    previous_issues: Optional[List[str]] = None,
) -> Examples:
    """Generate bilingual example phrases using the word and its translation."""

    # Base prompt
    prompt = f"Create 3 to 4 bilingual example sentences using '{source_word}' ({source_language}) and '{target_word}' ({target_language}). Real-life contexts, medium length, everyday conversations. The context should be in the source language {source_language}."

    # Quality requirements for examples
    quality_requirements = [
        "Examples are natural, conversational, and realistic",
        "Both original and translation are grammatically correct",
        "Examples demonstrate proper usage of the word in context",
        "Translations are accurate and natural in the target language",
        "Context notes are helpful and relevant",
        "Examples are diverse and show different use cases",
    ]

    # Add quality feedback if provided
    enhanced_prompt = add_quality_feedback_to_prompt(
        prompt, quality_feedback, previous_issues, quality_requirements
    )

    return await create_llm_response(
        response_model=Examples,
        user_prompt=enhanced_prompt,
    )
