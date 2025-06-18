from typing import Optional

from langchain.tools import tool
from pydantic import BaseModel, Field
from vocab_processor.constants import Language
from vocab_processor.tools.base_tool import create_llm_response


class ExampleSentence(BaseModel):
    """A bilingual example sentence with translation."""

    original: str = Field(
        ..., description="The example sentence in the source language", min_length=20
    )
    translation: str = Field(
        ...,
        description="The translation of the example sentence into the target language",
        min_length=20,
    )
    context: Optional[str] = Field(
        None,
        description="Optional context or usage note for the example in the source language",
    )


class Examples(BaseModel):
    examples: list[ExampleSentence] = Field(
        ...,
        description="List of example sentences using the word and its translation.",
        min_items=2,
        max_items=3,
    )


@tool
async def get_examples(
    source_word: str,
    target_word: str,
    source_language: Language,
    target_language: Language,
) -> Examples:
    """Generate bilingual example phrases using the word and its translation."""

    prompt = f"Create 2 to 3 bilingual example sentences using '{source_word}' ({source_language}) and '{target_word}' ({target_language}). Real-life contexts, medium length, everyday conversations. The context should be in the source language {source_language}."

    return await create_llm_response(
        response_model=Examples,
        user_prompt=prompt,
    )
