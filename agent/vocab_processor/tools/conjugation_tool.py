from langchain.tools import tool

from vocab_processor.constants import Language, PartOfSpeech, instructor_llm
from vocab_processor.schemas.english_conj_model import EnglishVerbConjugation
from vocab_processor.schemas.german_conj_model import GermanVerbConjugation
from vocab_processor.schemas.spanish_conj_model import SpanishVerbConjugation


@tool
async def get_conjugation(
    target_word: str, target_language: Language, target_part_of_speech: PartOfSpeech
) -> str:
    """Get full verb conjugation table for a given verb in the specified language and part of speech."""

    if not target_part_of_speech.is_conjugatable:
        return f"The word '{target_word}' is not a verb, so there is no conjugation table for it."

    if target_language == Language.ENGLISH:
        schema = EnglishVerbConjugation
    elif target_language == Language.GERMAN:
        schema = GermanVerbConjugation
    else:
        schema = SpanishVerbConjugation

    system_msg = f"You are an expert linguist specialized in {target_language} conjugations. **Output only JSON that strictly conforms to the expected schema. Do not explain or think anything.**"

    user_prompt = f"Please provide the conjugation for the {target_language} verb '{target_word}' in the {target_language} language."

    result = await instructor_llm.create(
        response_model=schema,
        messages=[
            {"role": "system", "content": system_msg},
            {"role": "user", "content": user_prompt},
        ],
    )

    return result.model_dump_json(indent=2)
