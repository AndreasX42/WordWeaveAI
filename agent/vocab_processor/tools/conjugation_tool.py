from langchain.tools import tool
from vocab_processor.constants import Language, PartOfSpeech
from vocab_processor.schemas.english_conj_model import EnglishVerbConjugation
from vocab_processor.schemas.german_conj_model import GermanVerbConjugation
from vocab_processor.schemas.spanish_conj_model import SpanishVerbConjugation
from vocab_processor.tools.base_tool import (
    create_llm_response,
    create_tool_error_response,
)


@tool
async def get_conjugation(
    target_word: str, target_language: Language, target_part_of_speech: PartOfSpeech
) -> str:
    """Get full verb conjugation table for a given verb in the specified language and part of speech."""

    if not target_part_of_speech.is_conjugatable:
        return f"The word '{target_word}' is not a verb, so there is no conjugation table for it."

    try:
        # Select appropriate schema based on language
        schema_map = {
            Language.ENGLISH: EnglishVerbConjugation,
            Language.GERMAN: GermanVerbConjugation,
            Language.SPANISH: SpanishVerbConjugation,
        }
        schema = schema_map[target_language]

        prompt = f"Create conjugation table for {target_language} verb '{target_word}'. Output JSON only."

        result = await create_llm_response(
            response_model=schema,
            user_prompt=prompt,
        )

        return result.model_dump_json(indent=2)

    except Exception as e:
        context = {
            "target_word": target_word,
            "target_language": target_language,
            "target_part_of_speech": target_part_of_speech,
        }
        error_response = create_tool_error_response(e, context)
        return f"Error creating conjugation: {error_response}"
