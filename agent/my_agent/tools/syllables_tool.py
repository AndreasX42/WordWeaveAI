from langchain.tools import tool
from my_agent.constants import Language, instructor_llm
from pydantic import BaseModel, Field
from typing import List

class SyllableBreakdown(BaseModel):
    syllables: List[str] = Field(..., description="List of syllables for the word")
    phonetic_guide: str = Field(..., description="Phonetic pronunciation guide")

@tool
async def get_syllables(target_word: str, target_language: Language) -> SyllableBreakdown:
    """Break down a word into syllables with phonetic guidance."""
    
    system_prompt = f"""You are an expert linguist specializing in {target_language.value} pronunciation and syllable division.

Break down the given word into syllables following standard {target_language.value} syllable division rules.

Guidelines:
- Each syllable should be pronounceable on its own
- Follow standard {target_language.value} syllable patterns
- Include stress markers if relevant (primary stress with ˈ, secondary with ˌ)
- Provide a phonetic guide using IPA or common pronunciation symbols

Examples for {target_language.value}:
English: "beautiful" → ["beau", "ti", "ful"], phonetic: "/ˈbjuː.tɪ.fəl/"
Spanish: "hermoso" → ["her", "mo", "so"], phonetic: "/er.ˈmo.so/"
German: "schön" → ["schön"], phonetic: "/ʃøːn/"
"""

    user_prompt = f"Break down the {target_language.value} word '{target_word}' into syllables and provide phonetic guidance."
    
    return await instructor_llm.create(
        response_model=SyllableBreakdown,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ],
    ) 