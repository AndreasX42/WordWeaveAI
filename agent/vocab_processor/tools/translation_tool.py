from typing import Optional

from langchain.tools import tool
from pydantic import BaseModel, Field

from vocab_processor.constants import Language, PartOfSpeech
from vocab_processor.prompts import TRANSLATION_PROMPT_TEMPLATE
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
        description=f"Article of the translated word in the target language, if it is a noun.",
    )
    target_additional_info: str | None = Field(
        None,
        description="Additional information in the source language about the translation in the target language if needed. For example if the word is only common in a specific country or region, in what context the word is used, if it is colloquial or vulgar, etc.",
    )
    target_plural_form: str | None = Field(
        None,
        description="Plural form of the translated word in the target language if it is a noun.",
    )
    english_word: str = Field(
        description="The English translation of the target word including article if it is a proper noun or 'to' if it is a verb"
    )


class TranslationResponse(BaseModel):
    result: Translation
    prompt: str


@tool
async def get_translation(
    source_word: str,
    source_language: Language,
    target_language: Language,
    source_part_of_speech: PartOfSpeech,
    quality_feedback: Optional[str] = None,
    previous_issues: Optional[list[str]] = None,
    suggestions: Optional[list[str]] = None,
) -> TranslationResponse:
    """Translate a word between supported languages English, German and Spanish and categorize the part of speech."""

    enhanced_prompt = TRANSLATION_PROMPT_TEMPLATE.build_enhanced_prompt(
        quality_feedback=quality_feedback,
        previous_issues=previous_issues,
        suggestions=suggestions,
        source_word=source_word,
        source_language=source_language.value,
        target_language=target_language.value,
        source_part_of_speech=source_part_of_speech.value,
    )

    result = await create_llm_response(
        response_model=Translation,
        user_prompt=enhanced_prompt,
    )

    return TranslationResponse(result=result, prompt=enhanced_prompt)
