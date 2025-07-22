from typing import Optional, get_args

from langchain_core.tools import tool
from pydantic import BaseModel

from vocab_processor.constants import Language, PartOfSpeech
from vocab_processor.prompts_simple import CONJUGATION_PROMPT_TEMPLATE
from vocab_processor.schemas.english_conj_model import EnglishVerbConjugation
from vocab_processor.schemas.german_conj_model import GermanVerbConjugation
from vocab_processor.schemas.spanish_conj_model import SpanishVerbConjugation
from vocab_processor.tools.base_tool import (
    create_llm_response,
    create_tool_error_response,
)


def _get_expected_tenses_for_language(target_language: Language) -> str:
    """Extract expected tenses from schema modules and format for prompt."""

    if target_language == Language.ENGLISH:
        import vocab_processor.schemas.english_conj_model as eng

        tenses = {
            "Non Personal Forms": list(get_args(eng.NonPersonalForms)),
            "Indicative": list(get_args(eng.IndicativeTenses)),
            "Subjunctive": list(get_args(eng.SubjunctiveTenses)),
        }
    elif target_language == Language.GERMAN:
        import vocab_processor.schemas.german_conj_model as ger

        tenses = {
            "Non Personal Forms": list(get_args(ger.NonPersonalForms)),
            "Indikativ": list(get_args(ger.IndicativeTenses)),
            "Konjunktiv": list(get_args(ger.SubjunctiveTenses)),
        }
    elif target_language == Language.SPANISH:
        import vocab_processor.schemas.spanish_conj_model as spa

        tenses = {
            "Non Personal Forms": list(get_args(spa.NonPersonalForms)),
            "Indicative": list(get_args(spa.IndicativeTenses)),
            "Subjunctive": list(get_args(spa.SubjunctiveTenses)),
        }
    else:
        return ""

    tenses_text = f"\n**Expected Tenses for {target_language.value}:**\n"
    for category, tense_list in tenses.items():
        tenses_text += f"- {category}: {', '.join(tense_list)}\n"

    return tenses_text


class ConjugationResponse(BaseModel):
    result: str
    prompt: str


@tool
async def get_conjugation(
    target_word: str,
    target_language: Language,
    target_part_of_speech: PartOfSpeech,
    quality_feedback: Optional[str] = None,
    previous_issues: Optional[list[str]] = None,
    suggestions: Optional[list[str]] = None,
) -> ConjugationResponse:
    """Get full verb conjugation table for a given verb in the specified language and part of speech."""

    if not target_part_of_speech.is_conjugatable:
        # This case does not have a prompt.
        return ConjugationResponse(
            result=f"The word '{target_word}' is not a verb, so there is no conjugation table for it.",
            prompt="",
        )

    try:
        # Select appropriate schema based on language
        schema_map = {
            Language.ENGLISH: EnglishVerbConjugation,
            Language.GERMAN: GermanVerbConjugation,
            Language.SPANISH: SpanishVerbConjugation,
        }
        schema = schema_map[target_language]

        enhanced_prompt = CONJUGATION_PROMPT_TEMPLATE.build_enhanced_prompt(
            quality_feedback=quality_feedback,
            previous_issues=previous_issues,
            suggestions=suggestions,
            target_language=target_language.value,
            target_word=target_word,
            expected_tenses=_get_expected_tenses_for_language(target_language),
        )

        result = await create_llm_response(
            response_model=schema,
            user_prompt=enhanced_prompt,
        )

        return ConjugationResponse(
            result=result.model_dump_json(indent=2), prompt=enhanced_prompt
        )

    except Exception as e:
        context = {
            "target_word": target_word,
            "target_language": target_language,
            "target_part_of_speech": target_part_of_speech,
        }
        error_response = create_tool_error_response(e, context)
        return ConjugationResponse(
            result=f"Error creating conjugation: {error_response}",
            prompt="",
        )
