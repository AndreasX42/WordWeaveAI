from typing import List, Optional

from langchain.tools import tool
from pydantic import BaseModel, Field

from vocab_processor.constants import Language, PartOfSpeech
from vocab_processor.tools.base_tool import (
    add_quality_feedback_to_prompt,
    create_llm_response,
)


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
    english_word: str = Field(
        description="The English translation of the target word including article if it is a proper noun or 'to' if it is a verb"
    )


@tool
async def get_translation(
    source_word: str,
    source_language: Language,
    target_language: Language,
    source_part_of_speech: PartOfSpeech,
    quality_feedback: Optional[str] = None,
    previous_issues: Optional[List[str]] = None,
    suggestions: Optional[List[str]] = None,
) -> Translation:
    """Translate a word between supported languages English, German and Spanish and categorize the part of speech."""

    # Base prompt
    prompt = f"""Translate '{source_word}' ({source_language}→{target_language}). 

Source POS: {source_part_of_speech}

IMPORTANT: For target_part_of_speech, use correct values for {target_language} if it is a noun:
- English: "noun" (English has no grammatical gender)
- German: "masculine noun", "feminine noun", or "neuter noun" 
- Spanish: "masculine noun" or "feminine noun"

For target_article in case of noun:
- English: null (no articles needed)
- German: der/die/das
- Spanish: el/la/los/las

Provide most common translation, appropriate POS, article if needed, and additional info for register/context."""

    # Quality requirements for translation
    quality_requirements = [
        f"Use correct part of speech for {target_language}",
        f"Match the register and tone of the source word:",
        f"- If source is informal/slang, provide informal translation",
        f"- If source is vulgar, note this and provide appropriate equivalent",
        f"For slang/colloquial words, provide the most natural equivalent learners would encounter",
        f"Use target_additional_info to explain context, register, and regional usage in {source_language}",
        f"For informal/vulgar words like 'huevada', consider translations like 'bullshit', 'crap', 'nonsense' and explain the register.",
        f"Provide the english translation of the target word in 'english_word', including article if it is a proper noun or 'to' if it is a verb",
        f"Provide only the base form of the translated source word in 'target_word' without any articles or other modifiers",
    ]

    # Add quality feedback if provided
    enhanced_prompt = add_quality_feedback_to_prompt(
        prompt, quality_feedback, previous_issues, suggestions, quality_requirements
    )

    return await create_llm_response(
        response_model=Translation,
        user_prompt=enhanced_prompt,
    )
