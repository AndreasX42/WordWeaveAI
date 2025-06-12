from langchain.tools import tool
from my_agent.constants import instructor_llm, Language
from pydantic import BaseModel, Field
from typing import Optional

class ExampleSentence(BaseModel):
    """A bilingual example sentence with translation."""
    original: str = Field(..., description="The example sentence in the original language", min_length=15)
    translation: str = Field(..., description="The translation of the example sentence", min_length=15)
    context: Optional[str] = Field(None, description="Optional context or usage note for the example")

class Examples(BaseModel):
    examples: list[ExampleSentence] = Field(..., description="List of example sentences using the word and its translation.")


@tool
async def get_examples(source_word: str, target_word: str, source_language: Language, target_language: Language) -> str:
    """Generate 2 bilingual example phrases using the word and its translation."""
    
    system_prompt = f"""You are an expert linguist and teacher specialized in providing examples of how to use words in everyday conversations.
    """
    
    user_prompt = f"""Give 2 example sentences using the {source_language} word '{source_word}' and its {target_language} translation '{target_word}', with both {source_language} and {target_language} versions. The sentences should be of medium length and commonly used in everyday conversations in {target_language} and appropriate for a {target_language} learner. The context should be a real-life situation and also in the {source_language}.
    """

    return await instructor_llm.create(
        response_model=Examples,
        messages=[{"role": "system", "content": system_prompt},{"role": "user", "content": user_prompt}],
    )