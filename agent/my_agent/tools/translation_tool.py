from langchain.tools import tool
from my_agent.constants import instructor_llm, PartOfSpeech, Language
from pydantic import BaseModel, Field

class Translation(BaseModel):
    target_word: str = Field(..., description="Translation of the word into the target language")
    target_part_of_speech: PartOfSpeech = Field(..., description="Part of speech of the word")
    
@tool
async def get_translation(source_word: str, source_language: Language, target_language: Language, source_part_of_speech: PartOfSpeech) -> Translation:
    """Translate a word between supported languages English, German and Spanish and categorize the part of speech."""
    
    system_prompt = f"""You are an expert linguist and teacher specialized in translating words between all languages, categorizing the part of speech.
    """
    
    user_prompt = f"""Translate the word '{source_word}' from {source_language} to {target_language} taking into account the part of speech of the original word: {source_part_of_speech}.
    Return only the most commonly used translation, the part of speech should be the same as the part of speech of the original word.
    """
    
    return await instructor_llm.create(
        response_model=Translation,
        messages=[{"role": "system", "content": system_prompt},{"role": "user", "content": user_prompt}],
    )


