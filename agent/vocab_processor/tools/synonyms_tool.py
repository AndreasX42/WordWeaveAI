from typing import Optional

from langchain.tools import tool
from pydantic import BaseModel, Field

from vocab_processor.constants import Language, PartOfSpeech
from vocab_processor.prompts import SYNONYMS_PROMPT_TEMPLATE
from vocab_processor.tools.base_tool import create_llm_response


class Synonym(BaseModel):
    """Synonyms of the word in the specified language."""

    synonym: str = Field(
        ..., description="Commonly used synonym of the word in the target language"
    )
    explanation: str = Field(
        ...,
        max_length=200,
        description="Explanation of the synonym in the source language",
    )


class Synonyms(BaseModel):
    """List of synonyms in the target language."""

    note: Optional[str] = Field(
        None,
        max_length=200,
        description="Note in the source language about the synonyms, for example, if no direct synonym exists.",
    )
    synonyms: list[Synonym] = Field(
        ...,
        description="List of synonyms of the target word in the target language",
        min_length=0,
        max_length=3,
    )


class SynonymsResponse(BaseModel):
    result: Synonyms
    prompt: str


@tool
async def get_synonyms(
    target_word: str,
    source_language: Language,
    target_language: Language,
    target_part_of_speech: PartOfSpeech,
    quality_feedback: Optional[str] = None,
    previous_issues: Optional[list[str]] = None,
    suggestions: Optional[list[str]] = None,
) -> SynonymsResponse:
    """Return synonyms of the word in the specified language."""

    enhanced_prompt = SYNONYMS_PROMPT_TEMPLATE.build_enhanced_prompt(
        quality_feedback=quality_feedback,
        previous_issues=previous_issues,
        suggestions=suggestions,
        target_word=target_word,
        source_language=source_language.value,
        target_language=target_language.value,
        target_part_of_speech=target_part_of_speech.value,
    )

    result = await create_llm_response(
        response_model=Synonyms,
        user_prompt=enhanced_prompt,
    )

    return SynonymsResponse(result=result, prompt=enhanced_prompt)
