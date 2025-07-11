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
    source_language: Optional[Language] = Field(
        None,
        description="The language of the source word, if provided by the user. If not provided, it will be detected by the classification step.",
    )
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
    source_additional_info: Optional[str] = Field(
        None,
        description="Additional information about the word in the source language if needed. For example if the word is only common in a specific country or region.",
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
    target_phonetic_guide: Optional[str] = Field(
        None, description="Phonetic guide for the translated word."
    )
    target_additional_info: Optional[str] = Field(
        None,
        description="Additional information about the translation in the target language if needed. For example if the word is only common in a specific country or region.",
    )

    # Fields from enrichment steps
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
    media_adapted: Optional[bool] = Field(
        None,
        description="True if media was adapted from one language to another.",
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
    media_ref: Optional[str] = Field(
        None,
        description="Reference to media object in the ddb media table.",
    )
    examples: Optional[List[ExampleSentence]] = Field(
        None, description="Example sentences using the target word."
    )
    conjugation: Optional[Any] = Field(
        None,
        description="Conjugation table or data for the target word if it's a verb.",
    )

    # Quality tracking fields
    validation_quality_approved: Optional[bool] = Field(
        None, description="Whether validation step passed quality gate."
    )
    classification_quality_approved: Optional[bool] = Field(
        None, description="Whether classification step passed quality gate."
    )
    translation_quality_approved: Optional[bool] = Field(
        None, description="Whether translation step passed quality gate."
    )
    media_quality_approved: Optional[bool] = Field(
        None, description="Whether media step passed quality gate."
    )
    examples_quality_approved: Optional[bool] = Field(
        None, description="Whether examples step passed quality gate."
    )
    synonyms_quality_approved: Optional[bool] = Field(
        None, description="Whether synonyms step passed quality gate."
    )
    syllables_quality_approved: Optional[bool] = Field(
        None, description="Whether syllables step passed quality gate."
    )
    pronunciation_quality_approved: Optional[bool] = Field(
        None, description="Whether pronunciation step passed quality gate."
    )
    conjugation_quality_approved: Optional[bool] = Field(
        None, description="Whether conjugation step passed quality gate."
    )

    # Retry counts for each tool
    validation_retry_count: Optional[int] = Field(default=0)
    classification_retry_count: Optional[int] = Field(default=0)
    translation_retry_count: Optional[int] = Field(default=0)
    media_retry_count: Optional[int] = Field(default=0)
    examples_retry_count: Optional[int] = Field(default=0)
    synonyms_retry_count: Optional[int] = Field(default=0)
    syllables_retry_count: Optional[int] = Field(default=0)
    pronunciation_retry_count: Optional[int] = Field(default=0)
    conjugation_retry_count: Optional[int] = Field(default=0)

    # Quality scores for monitoring
    validation_quality_score: Optional[float] = Field(None)
    classification_quality_score: Optional[float] = Field(None)
    translation_quality_score: Optional[float] = Field(None)
    media_quality_score: Optional[float] = Field(None)
    examples_quality_score: Optional[float] = Field(None)
    synonyms_quality_score: Optional[float] = Field(None)
    syllables_quality_score: Optional[float] = Field(None)
    pronunciation_quality_score: Optional[float] = Field(None)
    conjugation_quality_score: Optional[float] = Field(None)

    # Supervisor coordination fields
    sequential_quality_passed: Optional[bool] = Field(None)
    failed_quality_steps: Optional[List[str]] = Field(None)
    parallel_tasks_to_execute: Optional[List[str]] = Field(None)
    completed_parallel_tasks: Optional[List[str]] = Field(
        None, description="List of parallel tasks that have completed"
    )
    parallel_tasks_complete: Optional[bool] = Field(
        None, description="Whether all parallel tasks have completed"
    )
    overall_quality_score: Optional[float] = Field(None)
    quality_checks_passed: Optional[int] = Field(None)
    quality_checks_failed: Optional[int] = Field(None)
    processing_complete: Optional[bool] = Field(None)

    class Config:
        arbitrary_types_allowed = True
