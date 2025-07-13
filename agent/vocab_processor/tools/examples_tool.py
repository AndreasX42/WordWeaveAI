from typing import List, Optional

from langchain.tools import tool
from pydantic import BaseModel, Field

from vocab_processor.constants import Language
from vocab_processor.tools.base_tool import (
    add_quality_feedback_to_prompt,
    create_llm_response,
    create_tool_error_response,
)


class ExampleSentence(BaseModel):
    """A bilingual example sentence with translation."""

    original: str = Field(
        ..., description="The example sentence in the source language", min_length=30
    )
    translation: str = Field(
        ...,
        description="The translation of the example sentence into the target language",
        min_length=30,
    )
    context: Optional[str] = Field(
        ...,
        description="Context or usage note for the example in the source language",
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
    suggestions: Optional[List[str]] = None,
) -> Examples:
    """Generate bilingual example phrases using the word and its translation."""

    # Base prompt
    prompt = f"Create 3-4 natural examples using '{source_word}' ({source_language}) and '{target_word}' ({target_language}). Context in {source_language}."

    # Quality requirements for examples
    quality_requirements = [
        "Natural, conversational examples",
        "Grammatically correct in both languages",
        "Proper word usage in context",
        "Natural translations",
        "Helpful context notes",
        "Show different use cases",
    ]

    # Add quality feedback if provided
    enhanced_prompt = add_quality_feedback_to_prompt(
        prompt, quality_feedback, previous_issues, suggestions, quality_requirements
    )

    return await create_llm_response(
        response_model=Examples,
        user_prompt=enhanced_prompt,
    )
