from langchain.tools import tool
from pydantic import BaseModel, Field

from vocab_processor.constants import Language, PartOfSpeech, instructor_llm


class Translation(BaseModel):
    target_word: str = Field(
        ..., description="Translation of the word into the target language"
    )
    target_part_of_speech: PartOfSpeech = Field(
        ..., description="Part of speech of the word"
    )
    target_article: str | None = Field(
        None,
        description="Article of the word in the target language, if it is a noun",
    )


@tool
async def get_translation(
    source_word: str,
    source_language: Language,
    target_language: Language,
    source_part_of_speech: PartOfSpeech,
) -> Translation:
    """Translate a word between supported languages English, German and Spanish and categorize the part of speech."""

    system_prompt = f"""You are an expert linguist and teacher specialized in translating words between all languages, categorizing the part of speech.
    """

    user_prompt = f"""Translate the word '{source_word}' from {source_language} to {target_language} taking into account the part of speech of the original word: {source_part_of_speech}.
    Return only the most commonly used translation, the part of speech should be the same as the part of speech of the original word.
    If the word is a noun, return the article of the word in the target language. If the word is not a noun, return null. For example, if the target word is 'casa' in spanish, return 'la'.
    """

    return await instructor_llm.create(
        response_model=Translation,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
    )
