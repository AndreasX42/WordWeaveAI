from langchain.tools import tool
from my_agent.constants import instructor_llm, Language
from my_agent.schemas.visual_model import PhotoOption, Media
from dotenv import load_dotenv
import os
import aiohttp
from pydantic import BaseModel, Field

load_dotenv()

PEXELS_API_KEY = os.getenv("PEXELS_API_KEY")
PEXELS_PHOTO_SEARCH_URL = "https://api.pexels.com/v1/search"


async def fetch_photos(query: str, per_page: int = 3) -> list[PhotoOption]:
    async with aiohttp.ClientSession() as session:
        async with session.get(
            PEXELS_PHOTO_SEARCH_URL,
            headers={"Authorization": PEXELS_API_KEY},
            params={
                "query": query,
                "orientation": "landscape",
                "per_page": per_page,
                "size": "large"
            },
            timeout=aiohttp.ClientTimeout(total=10)
        ) as response:
            if response.status != 200:
                response_text = await response.text()
                raise RuntimeError(
                    f"Pexels API failed ({response.status}): {response_text}"
                )

            data = await response.json()
            photos_data = data.get("photos", [])
            
            for photo in photos_data:
                photo["src"] = {"large2x": photo["src"]["large2x"], "small": photo["src"]["small"]}
    
            return [PhotoOption(**photo) for photo in photos_data]


@tool
async def get_media(source_word: str, target_word: str, source_language: Language, target_language: Language) -> Media:
    """
    Get the most memorable photo for a vocabulary word.
    Steps:
    1. Translate word to English with descriptors
    2. Fetch Pexels photos
    3. Ask LLM to choose the best one
    """

    class PhotoSearchQuery(BaseModel):
        query: str = Field(description="English search query plus two descriptive synonyms to find the most relevant photos in Pexels")

    try:
        # translate to english and get criteria
        query_prompt = f"""
        Given the {source_language} word '{source_word}', respond with:
        `query` – an English search query plus a few descriptive synonyms to find the most relevant photos in Pexels.

        Respond in the JSON format provided.
        """
        result_query = await instructor_llm.create(response_model=PhotoSearchQuery, messages=[{"role": "user", "content": query_prompt}])

        photos = await fetch_photos(result_query.query, per_page=10)

        if not photos:
            return Media(photo_url="", photographer="", alt_description="No photos found matching the query.")

        rank_prompt = f"""Find the most adquate photo for the following criteria that best depitcts the {source_language} word '{source_word}' that makes it easy to remember the {target_language} word '{target_word}'.

        Photos:
        {[p.model_dump() for p in photos]}

        Respond only in the JSON format provided.
        """

        system_prompt = f"""You are an expert linguist and teacher specialized in finding the most memorable photo for a vocabulary word such that the learner can easily remember it.
        """

        result_media = await instructor_llm.create(
            response_model=Media,
            messages=[{"role": "system", "content": system_prompt},{"role": "user", "content": rank_prompt}],
        )

        return result_media
            
    except Exception as e:
        print(f"Error in get_media: {e}")
        return Media(photo_url="", photographer="", alt_description=f"Error generating visual media: {str(e)}")
