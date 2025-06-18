from typing import Any, List, Optional

from pydantic import BaseModel, Field
from vocab_processor.constants import Language, PartOfSpeech
from vocab_processor.schemas.media_model import Media
from vocab_processor.tools.examples_tool import ExampleSentence
from vocab_processor.tools.synonyms_tool import Synonym
from vocab_processor.tools.validation_tool import SuggestedWordInfo


class VocabState(BaseModel):
    # Inputs from user
    source_word: str = Field(..., description="The initial word provided by the user.")
    target_language: Language = Field(
        ..., description="The target language for translation and other operations."
    )

    # Fields from validation step
    validation_passed: Optional[bool] = Field(
        None, description="Whether the source word passed initial validation."
    )
    validation_message: Optional[str] = Field(
        None,
        description="Message from the validation step, explaining issues or confirming validity.",
    )
    suggested_words: Optional[List[SuggestedWordInfo]] = Field(
        None,
        description="Suggested corrections or alternatives from the validation step.",
    )

    # source_language can be populated by validation or classification
    # If validation provides it and is valid, classification might refine or confirm it.
    source_language: Optional[Language] = Field(
        None, description="The detected language of the source word."
    )

    # Fields from classification step
    source_definition: Optional[list[str]] = Field(
        None, description="Definitions of the source word in its language."
    )
    source_part_of_speech: Optional[PartOfSpeech] = Field(
        None, description="Part of speech of the source word."
    )
    source_article: Optional[str] = Field(
        None,
        description="Article of the source word in the source language, if it is a noun.",
    )

    # Fields from translation step
    target_word: Optional[str] = Field(
        None, description="The translated word in the target language."
    )
    target_part_of_speech: Optional[PartOfSpeech] = Field(
        None, description="Part of speech of the translated word."
    )
    target_article: Optional[str] = Field(
        None,
        description="Article of the translated word in the target language if it is a noun.",
    )
    target_syllables: Optional[list[str]] = Field(
        None, description="Syllables of the translated word."
    )

    # Fields from enrichment steps
    # If Synonym, ExampleSentence, Media, etc. are Pydantic models, use them here for better type safety.
    english_word: Optional[str] = Field(
        None, description="The English word for the target word."
    )
    search_query: Optional[list[str]] = Field(
        None,
        description="The list of English search words used for Pexels lookup.",
    )
    media_reused: Optional[bool] = Field(
        None,
        description="True if media was reused from cache instead of fetched from Pexels.",
    )

    synonyms: Optional[List[Synonym]] = Field(
        None, description="List of synonyms for the target word."
    )
    pronunciations: Optional[str] = Field(
        None,
        description="Audio data (base64) or URL for pronunciation of the target word.",
    )
    media: Optional[Media] = Field(
        None,
        description="Visual media (e.g., image URLs or objects) related to the word.",
    )
    examples: Optional[List[ExampleSentence]] = Field(
        None, description="Example sentences using the target word."
    )
    conjugation: Optional[Any] = Field(
        None,
        description="Conjugation table or data for the target word if it's a verb.",
    )

    class Config:
        arbitrary_types_allowed = True
