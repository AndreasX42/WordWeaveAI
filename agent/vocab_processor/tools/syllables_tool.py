from typing import Optional

from aws_lambda_powertools import Logger
from langchain.tools import tool
from pydantic import BaseModel, Field

from vocab_processor.constants import Language
from vocab_processor.prompts import SYLLABLES_PROMPT_TEMPLATE
from vocab_processor.tools.base_tool import create_llm_response

logger = Logger(service="vocab-processor")


class SyllableBreakdown(BaseModel):
    """Syllable breakdown and phonetic guide for a word."""

    syllables: list[str] = Field(
        ...,
        description="List array of syllables that make up the word.",
    )
    phonetic_guide: str = Field(
        ...,
        description="Simple, learner-friendly phonetic guide for the word.",
    )


class SyllablesResponse(BaseModel):
    result: SyllableBreakdown
    prompt: str


@tool
async def get_syllables(
    target_word: str,
    target_language: Language,
    quality_feedback: Optional[str] = None,
    previous_issues: Optional[list[str]] = None,
    suggestions: Optional[list[str]] = None,
) -> SyllablesResponse:
    """Break down a word into syllables with phonetic guidance."""

    enhanced_prompt = SYLLABLES_PROMPT_TEMPLATE.build_enhanced_prompt(
        quality_feedback=quality_feedback,
        previous_issues=previous_issues,
        suggestions=suggestions,
        target_word=target_word,
        target_language=target_language.value,
    )

    result = await create_llm_response(
        response_model=SyllableBreakdown,
        user_prompt=enhanced_prompt,
    )
    return SyllablesResponse(result=result, prompt=enhanced_prompt)
