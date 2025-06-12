from pydantic import BaseModel, Field
from typing import List, Optional, Any
from my_agent.tools.synonyms_tool import Synonym
from my_agent.tools.examples_tool import ExampleSentence
from my_agent.schemas.visual_model import Media
from my_agent.tools.validation_tool import SuggestedWordInfo
from my_agent.constants import Language, PartOfSpeech


class VocabState(BaseModel):
    # Inputs from user
    source_word: str = Field(..., description="The initial word provided by the user.")
    target_language: Language = Field(..., description="The target language for translation and other operations.")

    # Fields from validation step
    validation_passed: Optional[bool] = Field(None, description="Whether the source word passed initial validation.")
    validation_message: Optional[str] = Field(None, description="Message from the validation step, explaining issues or confirming validity.")
    suggested_words: Optional[List[SuggestedWordInfo]] = Field(None, description="Suggested corrections or alternatives from the validation step.")
    
    # source_language can be populated by validation or classification
    # If validation provides it and is valid, classification might refine or confirm it.
    source_language: Optional[Language] = Field(None, description="The detected language of the source word.")

    # Fields from classification step
    source_definition: Optional[list[str]] = Field(None, description="Definitions of the source word in its language.")
    source_part_of_speech: Optional[PartOfSpeech] = Field(None, description="Part of speech of the source word.")
    
    # Fields from translation step
    target_word: Optional[str] = Field(None, description="The translated word in the target language.")
    target_part_of_speech: Optional[PartOfSpeech] = Field(None, description="Part of speech of the translated word.")
    target_syllables: Optional[list[str]] = Field(None, description="Syllables of the translated word.")

    # Fields from enrichment steps
    # If Synonym, ExampleSentence, Media, etc. are Pydantic models, use them here for better type safety.
    synonyms: Optional[List[Synonym]] = Field(None, description="List of synonyms for the target word.")
    pronunciations: Optional[str] = Field(None, description="Audio data (base64) or URL for pronunciation of the target word.")
    media: Optional[Media] = Field(None, description="Visual media (e.g., image URLs or objects) related to the word.")
    examples: Optional[List[ExampleSentence]] = Field(None, description="Example sentences using the target word.")
    conjugation: Optional[Any] = Field(None, description="Conjugation table or data for the target word if it's a verb.")

    class Config:
        arbitrary_types_allowed = True