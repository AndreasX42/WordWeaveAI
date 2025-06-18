from langchain.tools import tool
from pydantic import BaseModel, Field
from vocab_processor.constants import Language, PartOfSpeech
from vocab_processor.tools.base_tool import create_llm_response


class Translation(BaseModel):
    """Translation of a word into the target language with part of speech and article."""

    target_word: str = Field(
        ..., description="Translation of the word into the target language"
    )
    target_part_of_speech: PartOfSpeech = Field(
        ..., description="Part of speech of the translated word in the target language"
    )
    target_article: str | None = Field(
        None,
        description="Article of the translated word in the target language, if it is a noun",
    )


@tool
async def get_translation(
    source_word: str,
    source_language: Language,
    target_language: Language,
    source_part_of_speech: PartOfSpeech,
) -> Translation:
    """Translate a word between supported languages English, German and Spanish and categorize the part of speech."""

    prompt = f"Translate '{source_word}' ({source_language}→{target_language}). POS: {source_part_of_speech}. Return most common translation, POS, include article if noun."

    return await create_llm_response(
        response_model=Translation,
        user_prompt=prompt,
    )
