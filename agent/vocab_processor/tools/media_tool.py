import asyncio
import os
import uuid
from pathlib import Path

import aiofiles
import aiohttp
from dotenv import load_dotenv
from langchain.tools import tool
from pydantic import BaseModel, Field

from vocab_processor.constants import Language, instructor_llm
from vocab_processor.schemas.media_model import Media, PhotoOption

load_dotenv()

PEXELS_API_KEY = os.getenv("PEXELS_API_KEY")
PEXELS_PHOTO_SEARCH_URL = "https://api.pexels.com/v1/search"

# Base download directory
DOWNLOAD_FOLDER = os.getenv("DOWNLOAD_FOLDER", "downloads")


async def get_word_directory(target_language: Language, target_word: str) -> Path:
    """Create a directory specific to the target language and word (async)."""
    safe_word = "".join(c for c in target_word if c.isalnum())[:20]
    word_dir = Path(DOWNLOAD_FOLDER) / f"{target_language.name.lower()}_{safe_word}"

    # Use asyncio.to_thread to make mkdir non-blocking
    await asyncio.to_thread(word_dir.mkdir, parents=True, exist_ok=True)
    return word_dir


async def fetch_photos(query: str, per_page: int = 3) -> list[PhotoOption]:
    async with aiohttp.ClientSession() as session:
        async with session.get(
            PEXELS_PHOTO_SEARCH_URL,
            headers={"Authorization": PEXELS_API_KEY},
            params={
                "query": query,
                "orientation": "landscape",
                "per_page": per_page,
                "size": "large",
            },
            timeout=aiohttp.ClientTimeout(total=10),
        ) as response:
            if response.status != 200:
                response_text = await response.text()
                raise RuntimeError(
                    f"Pexels API failed ({response.status}): {response_text}"
                )

            data = await response.json()
            photos_data = data.get("photos", [])

            for photo in photos_data:
                photo["src"] = {
                    "large2x": photo["src"]["large2x"],
                    "small": photo["src"]["small"],
                }

            return [PhotoOption(**photo) for photo in photos_data]


async def download_image(url: str, file_path: Path) -> str:
    """Download an image from URL and save it to the specified path."""
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(
                url, timeout=aiohttp.ClientTimeout(total=30)
            ) as response:
                if response.status == 200:
                    async with aiofiles.open(file_path, "wb") as f:
                        async for chunk in response.content.iter_chunked(8192):
                            await f.write(chunk)
                    return str(file_path)
                else:
                    raise RuntimeError(
                        f"Failed to download image: HTTP {response.status}"
                    )
    except Exception as e:
        print(f"Error downloading image from {url}: {e}")
        return ""


@tool
async def get_media(
    source_word: str,
    target_word: str,
    source_language: Language,
    target_language: Language,
) -> Media:
    """
    Get the most memorable photo for a vocabulary word and download it locally.
    Steps:
    1. Translate word to English with descriptors
    2. Fetch Pexels photos
    3. Ask LLM to choose the best one
    4. Download both large2x and small versions to word-specific folder
    """

    class PhotoSearchQuery(BaseModel):
        query: str = Field(
            description="English search query plus two descriptive synonyms to find the most relevant photos in Pexels"
        )

    try:
        # translate to english and get criteria
        query_prompt = f"""
        Given the {source_language} word '{source_word}', respond with:
        `query` – an English search query plus a few descriptive synonyms to find the most relevant photos in Pexels.

        Respond in the JSON format provided.
        """
        result_query = await instructor_llm.create(
            response_model=PhotoSearchQuery,
            messages=[{"role": "user", "content": query_prompt}],
        )

        photos = await fetch_photos(result_query.query, per_page=10)

        if not photos:
            return Media(
                url="",
                alt="No photos found matching the query.",
                src={"large2x": "", "small": ""},
                explanation="No suitable images were found for this word.",
                memory_tip="Try visualizing the word concept in your mind.",
            )

        rank_prompt = f"""Find the most adequate photo for the following criteria that best depicts the {source_language} word '{source_word}' that makes it easy to remember the {target_language} word '{target_word}'.

        Photos:
        {[p.model_dump() for p in photos]}

        Respond only in the JSON format provided.
        """

        system_prompt = f"""You are an expert linguist and teacher specialized in finding the most memorable photo for a vocabulary word such that the learner can easily remember it.
        """

        result_media = await instructor_llm.create(
            response_model=Media,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": rank_prompt},
            ],
        )

        # Download the chosen images to word-specific folder
        if result_media.src.get("large2x") and result_media.src.get("small"):
            # Create word-specific directory (async)
            word_dir = await get_word_directory(target_language, target_word)

            # Generate filenames (no need for unique ID since each word has its own folder)
            large_filename = "image_large.jpg"
            small_filename = "image_small.jpg"

            large_path = word_dir / large_filename
            small_path = word_dir / small_filename

            # Download both versions
            large_result = await download_image(result_media.src["large2x"], large_path)
            small_result = await download_image(result_media.src["small"], small_path)

            # Update the src URLs to local file paths
            if large_result and small_result:
                # Make abspath calls async to avoid blocking os.getcwd()
                large_abspath = await asyncio.to_thread(os.path.abspath, large_result)
                small_abspath = await asyncio.to_thread(os.path.abspath, small_result)

                result_media.src = {
                    "large2x": f"file://{large_abspath}",
                    "small": f"file://{small_abspath}",
                }
                print(f"Images downloaded to: {word_dir}/")
            else:
                print("Failed to download one or both images, keeping original URLs")

        return result_media

    except Exception as e:
        print(f"Error in get_media: {e}")
        return Media(
            url="",
            alt=f"Error generating visual media: {str(e)}",
            src={"large2x": "", "small": ""},
            explanation="An error occurred while fetching the image.",
            memory_tip="Try creating a mental image of the word.",
        )
