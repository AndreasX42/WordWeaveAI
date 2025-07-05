from typing import List, Optional

from langchain.tools import tool
from pydantic import BaseModel, Field

from vocab_processor.constants import Language, PartOfSpeech
from vocab_processor.schemas.english_conj_model import EnglishVerbConjugation
from vocab_processor.schemas.german_conj_model import GermanVerbConjugation
from vocab_processor.schemas.spanish_conj_model import SpanishVerbConjugation
from vocab_processor.tools.base_tool import (
    add_quality_feedback_to_prompt,
    create_llm_response,
    create_tool_error_response,
)


class ConjugationResult(BaseModel):
    """Result of conjugation tool with the conjugation table."""

    conjugation: str = Field(
        ..., description="JSON string containing the conjugation table"
    )


@tool
async def get_conjugation(
    target_word: str,
    target_language: Language,
    target_part_of_speech: PartOfSpeech,
    quality_feedback: Optional[str] = None,
    previous_issues: Optional[List[str]] = None,
) -> ConjugationResult:
    """Get full verb conjugation table for a given verb in the specified language and part of speech."""

    if not target_part_of_speech.is_conjugatable:
        return ConjugationResult(
            conjugation=f"The word '{target_word}' is not a verb, so there is no conjugation table for it."
        )

    try:
        # Select appropriate schema based on language
        schema_map = {
            Language.ENGLISH: EnglishVerbConjugation,
            Language.GERMAN: GermanVerbConjugation,
            Language.SPANISH: SpanishVerbConjugation,
        }
        schema = schema_map[target_language]

        # Base prompt
        prompt = f"Create comprehensive conjugation table for {target_language} verb '{target_word}'. Include all essential forms learners need. Output JSON only."

        # Quality requirements for conjugation
        quality_requirements = [
            "Include the most common, essential verb forms learners need",
            "Follow natural, standard conjugation patterns for {target_language}",
            "All forms are grammatically correct and commonly used",
            "Include irregular forms if applicable with proper indication",
            "Conjugation table helps learners use the verb correctly in context",
            f"Include all required tenses and persons for {target_language}",
            "JSON structure matches the expected schema exactly",
        ]

        # Add quality feedback if provided
        enhanced_prompt = add_quality_feedback_to_prompt(
            prompt, quality_feedback, previous_issues, quality_requirements
        )

        result = await create_llm_response(
            response_model=schema,
            user_prompt=enhanced_prompt,
        )

        return ConjugationResult(conjugation=result.model_dump_json(indent=2))

    except Exception as e:
        context = {
            "target_word": target_word,
            "target_language": target_language,
            "target_part_of_speech": target_part_of_speech,
        }
        error_response = create_tool_error_response(e, context)
        return ConjugationResult(
            conjugation=f"Error creating conjugation: {error_response}"
        )
