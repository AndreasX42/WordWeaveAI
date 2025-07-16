from typing import Optional

from langchain.tools import tool
from pydantic import BaseModel, Field

from vocab_processor.constants import Language, PartOfSpeech
from vocab_processor.prompts import EXAMPLES_PROMPT_TEMPLATE
from vocab_processor.tools.base_tool import create_llm_response


class ExampleSentence(BaseModel):
    """A bilingual example sentence with translation."""

    original: str = Field(
        ..., description="The example sentence in the source language", min_length=30
    )
    translation: str = Field(
        ...,
        description="The translation of the example sentence into the target language",
        min_length=30,
    )
    context: Optional[str] = Field(
        ...,
        description="Context or usage note for the example in the source language",
    )


class Examples(BaseModel):
    examples: list[ExampleSentence] = Field(
        ...,
        description="List of example sentences using the word and its translation.",
        min_items=3,
        max_items=4,
    )


class ExamplesResponse(BaseModel):
    result: Examples
    prompt: str


@tool
async def get_examples(
    source_word: str,
    target_word: str,
    source_language: Language,
    target_language: Language,
    source_part_of_speech: PartOfSpeech,
    target_part_of_speech: PartOfSpeech,
    quality_feedback: Optional[str] = None,
    previous_issues: Optional[list[str]] = None,
    suggestions: Optional[list[str]] = None,
) -> ExamplesResponse:
    """Generate bilingual example phrases using the word and its translation."""

    enhanced_prompt = EXAMPLES_PROMPT_TEMPLATE.build_enhanced_prompt(
        quality_feedback=quality_feedback,
        previous_issues=previous_issues,
        suggestions=suggestions,
        source_word=source_word,
        source_language=source_language.value,
        target_word=target_word,
        target_language=target_language.value,
        source_part_of_speech=source_part_of_speech.value,
        target_part_of_speech=target_part_of_speech.value,
    )

    result = await create_llm_response(
        response_model=Examples,
        user_prompt=enhanced_prompt,
    )

    return ExamplesResponse(result=result, prompt=enhanced_prompt)
