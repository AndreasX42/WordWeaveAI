from langchain.tools import tool
from pydantic import BaseModel, Field
from vocab_processor.constants import Language, PartOfSpeech
from vocab_processor.tools.base_tool import create_llm_response


class WordCategorization(BaseModel):
    """Categorization of the word in the specified language."""

    source_definition: list[str] = Field(
        ...,
        min_items=1,
        max_items=3,
        description="Definitions of the word in its native language",
    )
    source_part_of_speech: PartOfSpeech = Field(
        ..., description="Part of speech of the source word"
    )
    source_article: str | None = Field(
        None,
        description="Article of the source word in the source language, if it is a noun",
    )


@tool
async def get_classification(
    source_word: str, source_language: Language
) -> WordCategorization:
    """Categorize part of speech and language."""

    prompt = f"Classify '{source_word}' ({source_language}): provide part of speech from {', '.join(PartOfSpeech.all_values())} and up to 3 definitions in {source_language}. If the word is a noun, provide the article."

    return await create_llm_response(
        response_model=WordCategorization,
        user_prompt=prompt,
    )
