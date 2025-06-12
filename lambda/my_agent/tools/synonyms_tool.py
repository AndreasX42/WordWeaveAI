from langchain.tools import tool
from my_agent.constants import instructor_llm, Language, PartOfSpeech

from pydantic import BaseModel, Field

class Synonym(BaseModel):
    synonym: str = Field(..., description="Synonym of the word")
    explanation: str = Field(..., description="Explanation of the synonym")
    
class Synonyms(BaseModel):
    synonyms: list[Synonym] = Field(..., description="List of synonyms in the original language")


@tool
async def get_synonyms(target_word: str, target_language: Language, target_part_of_speech: PartOfSpeech) -> Synonyms:
    """Return synonyms of the word in the specified language."""

    system_prompt = f"""You are an expert linguist and teacher specialized in providing synonyms for words in all languages.
    """
    
    user_prompt = f"Give 3 commonly used {target_part_of_speech} synonyms for the {target_language} word '{target_word}' in the lanuage {target_language}. The synonyms and the explanations should be {target_language}s." 
   
    return await instructor_llm.create(
        response_model=Synonyms,
        messages=[{"role": "system", "content": system_prompt},{"role": "user", "content": user_prompt}],
    )