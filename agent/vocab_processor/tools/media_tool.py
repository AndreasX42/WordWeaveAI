import os

import aiohttp
from langchain.tools import tool
from pydantic import BaseModel, Field
from vocab_processor.constants import Language, instructor_llm
from vocab_processor.schemas.media_model import Media, PhotoOption
from vocab_processor.utils.s3_utils import generate_vocab_s3_paths, upload_bytes_to_s3

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


async def download_and_upload_image(url: str, s3_key: str) -> str:
    """Download image from URL and upload directly to S3."""
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(
                url, timeout=aiohttp.ClientTimeout(total=30)
            ) as response:
                if response.status == 200:
                    # Read image data
                    image_data = await response.read()

                    # Upload directly to S3
                    return await upload_bytes_to_s3(image_data, s3_key, "image/jpeg")
                else:
                    raise RuntimeError(
                        f"Failed to download image: HTTP {response.status}"
                    )
    except Exception as e:
        print(f"Error downloading/uploading image from {url}: {e}")
        return f"Error: {str(e)}"


@tool
async def get_media(
    source_word: str,
    target_word: str,
    source_language: Language,
    target_language: Language,
) -> Media:
    """
    Get the most memorable photo for a vocabulary word and upload to S3.
    Steps:
    1. Translate word to English with descriptors
    2. Fetch Pexels photos
    3. Ask LLM to choose the best one
    4. Download and upload images directly to S3
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

        # Download and upload images directly to S3
        if (
            result_media.src
            and result_media.src.get("large2x")
            and result_media.src.get("small")
        ):
            # Generate S3 paths using centralized utility
            s3_paths = generate_vocab_s3_paths(target_language, target_word)
            image_prefix = s3_paths["image_prefix"]

            # Generate S3 keys for both sizes
            large_s3_key = f"{image_prefix}/large.jpg"
            small_s3_key = f"{image_prefix}/small.jpg"

            # Download and upload both versions directly to S3
            large_s3_url = await download_and_upload_image(
                result_media.src["large2x"], large_s3_key
            )
            small_s3_url = await download_and_upload_image(
                result_media.src["small"], small_s3_key
            )

            # Update URLs if uploads were successful
            if not large_s3_url.startswith("Error") and not small_s3_url.startswith(
                "Error"
            ):
                result_media.src = {
                    "large2x": large_s3_url,
                    "small": small_s3_url,
                }
                print(f"Images uploaded to S3: {image_prefix}/")
            else:
                print("Failed to upload images, keeping original URLs")

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
