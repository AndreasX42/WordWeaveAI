from langchain.tools import tool
from pydantic import BaseModel, Field
from vocab_processor.constants import Language, PartOfSpeech
from vocab_processor.tools.base_tool import create_llm_response


class Synonym(BaseModel):
    """Synonyms of the word in the specified language."""

    synonym: str = Field(..., description="Synonym of the word")
    explanation: str = Field(..., description="Explanation of the synonym")


class Synonyms(BaseModel):
    synonyms: list[Synonym] = Field(
        ..., description="List of synonyms in the original language"
    )


@tool
async def get_synonyms(
    target_word: str, target_language: Language, target_part_of_speech: PartOfSpeech
) -> Synonyms:
    """Return synonyms of the word in the specified language."""

    prompt = f"Provide 3 common {target_part_of_speech} synonyms for '{target_word}' in {target_language}. Include explanations in {target_language}."

    return await create_llm_response(
        response_model=Synonyms,
        user_prompt=prompt,
    )
