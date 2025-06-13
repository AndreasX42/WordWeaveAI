from langchain_core.tools import tool
from pydantic import BaseModel, Field

from vocab_processor.constants import Language, PartOfSpeech, instructor_llm


class WordCategorization(BaseModel):
    source_definition: list[str] = Field(
        ...,
        min_items=1,
        max_items=3,
        description="Definitions of the word its native language",
    )
    source_part_of_speech: PartOfSpeech = Field(
        ..., description="Part of speech of the word"
    )


@tool
async def get_classification(
    source_word: str, source_language: Language
) -> WordCategorization:
    """Categorize part of speech and language."""

    system_prompt = f"""You are an expert linguist and teacher specialized in categorizing words into all languages and parts of speech. 
    """

    user_prompt = f"""Classify the {source_language} word '{source_word}' into a part of speech and provide up to 3 definitions in its native language.
    Part of speech should be one of: {", ".join(PartOfSpeech.all_values())}.
    If the part of speech is not one of these, return 'Unknown'.
    """

    return await instructor_llm.create(
        response_model=WordCategorization,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
    )
