import os
from typing import Any

import aiohttp
from aws_lambda_powertools import Logger
from langchain.tools import tool
from pydantic import BaseModel, Field
from vocab_processor.constants import Language
from vocab_processor.schemas.media_model import Media, PhotoOption
from vocab_processor.tools.base_tool import (
    SystemMessages,
    create_llm_response,
    create_tool_error_response,
)
from vocab_processor.utils.ddb_utils import get_existing_media_for_search_words
from vocab_processor.utils.s3_utils import (
    generate_english_image_s3_paths,
    upload_bytes_to_s3,
)

logger = Logger(service="vocab-processor")

PEXELS_API_KEY = os.getenv("PEXELS_API_KEY")
PEXELS_PHOTO_SEARCH_URL = "https://api.pexels.com/v1/search"

# Reusable session configuration for better performance
_session_config = aiohttp.ClientTimeout(total=30, connect=5)


class TranslationResult(BaseModel):
    english_word: str = Field(description="The English translation of the target word")
    search_query: list[str] = Field(
        description="English search query plus descriptive synonyms to find the most relevant photos in Pexels",
        max_length=3,
        min_length=2,
    )


async def fetch_photos(query: str | list[str], per_page: int = 3) -> list[PhotoOption]:
    """Fetch photos from Pexels API."""
    # Convert list to space-separated string for Pexels API
    if isinstance(query, list):
        search_query = " ".join(query)
    else:
        search_query = query

    async with aiohttp.ClientSession(timeout=_session_config) as session:
        async with session.get(
            PEXELS_PHOTO_SEARCH_URL,
            headers={"Authorization": PEXELS_API_KEY},
            params={
                "query": search_query,
                "orientation": "landscape",
                "per_page": per_page,
                "size": "large",
            },
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


async def upload_to_s3(url: str, s3_key: str) -> str:
    """Download image from URL and upload directly to S3."""
    try:
        async with aiohttp.ClientSession(timeout=_session_config) as session:
            async with session.get(url) as response:
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
        logger.error("image_download_failed", url=url, s3_key=s3_key, error=str(e))
        return f"Error: {str(e)}"


@tool
async def get_media(
    source_word: str,
    target_word: str,
    source_language: Language,
    target_language: Language,
) -> dict[str, Any]:
    """
    Get the most memorable photo for a vocabulary word and upload to S3.
    Steps:
    1. Translate target word to English (ground truth for image storage)
    2. Check if images already exist in S3 under vocabs/en/{english_word}/images/*
    3. If not found, fetch Pexels photos using English translation
    4. Ask LLM to choose the best one
    5. Download and upload images directly to S3
    """

    try:
        # First, translate target word to English and get search criteria
        translation_prompt = f"For '{target_word}' ({target_language}): provide english_word + search_query (2-4 descriptive English terms for Pexels)."

        translation_result = await create_llm_response(
            response_model=TranslationResult,
            user_prompt=translation_prompt,
        )

        # STEP 1: Check if we already have Media object for any similar search words
        existing_media = await get_existing_media_for_search_words(
            translation_result.search_query
        )
        if existing_media:
            matched_word = existing_media.get("matched_word", "unknown")
            logger.info(
                f"Found existing Media object for search word '{matched_word}' (from query {translation_result.search_query}), reusing it"
            )

            # Pass raw DDB media data to LLM for translation and formatting
            adaptation_prompt = f"""Convert this existing media data to a Media object with texts translated to {source_language} for '{source_word}' ({source_language}) → '{target_word}' ({target_language}).

Existing media data: {existing_media}

Translate alt, explanation, and memory_tip to {source_language}. Keep url and src unchanged."""

            media = await create_llm_response(
                response_model=Media,
                user_prompt=adaptation_prompt,
                system_message=SystemMessages.MEDIA_SPECIALIST,
            )

            return {
                "media": media,
                "english_word": translation_result.english_word,
                "search_query": translation_result.search_query,
                "media_reused": True,
            }

        # STEP 2: If no database entry, fetch from Pexels API
        image_paths = generate_english_image_s3_paths(translation_result.english_word)
        large_key = image_paths["large_key"]
        small_key = image_paths["small_key"]

        logger.info(
            f"No existing Media found for search words {translation_result.search_query}, fetching from Pexels"
        )

        photos = await fetch_photos(translation_result.search_query, per_page=10)

        if not photos:
            return {
                "media": Media(
                    url="",
                    alt="No photos found matching the query.",
                    src={"large2x": "", "small": ""},
                    explanation="No suitable images were found for this word.",
                    memory_tip="Try visualizing the word concept in your mind.",
                )
            }

        rank_prompt = f"Choose best photo for '{source_word}' ({source_language}) → '{target_word}' ({target_language}). Translate the texts like in alt, explanation, memory_tip to the source language {source_language}. Photos: {[p.model_dump() for p in photos]}"

        result_media = await create_llm_response(
            response_model=Media,
            user_prompt=rank_prompt,
            system_message=SystemMessages.MEDIA_SPECIALIST,
        )

        # Download and upload images directly to S3
        if result_media.src and isinstance(result_media.src, dict):
            # Clean up any None keys or values in src dict
            cleaned_src = {
                k: v
                for k, v in result_media.src.items()
                if k is not None and v is not None
            }

            if cleaned_src.get("large2x") and cleaned_src.get("small"):
                try:
                    # Download and upload both versions directly to S3 using English-based paths
                    large_s3_url = await upload_to_s3(cleaned_src["large2x"], large_key)
                    small_s3_url = await upload_to_s3(cleaned_src["small"], small_key)

                    # Update URLs if uploads were successful
                    if not large_s3_url.startswith(
                        "Error"
                    ) and not small_s3_url.startswith("Error"):
                        result_media.src = {
                            "large2x": large_s3_url,
                            "small": small_s3_url,
                        }
                        logger.info(
                            f"Images uploaded to S3: {image_paths['image_prefix']}/"
                        )
                    else:
                        logger.info("Failed to upload images, keeping original URLs")

                except Exception as e:
                    logger.error(
                        "S3_upload_failed",
                        url=cleaned_src["large2x"],
                        s3_key=large_key,
                        error=str(e),
                    )
                    # Keep original URLs if S3 upload fails
            else:
                logger.info("Invalid src URLs for S3 upload")
        else:
            logger.info("No valid src data for S3 upload")

        return {
            "media": result_media,
            "english_word": translation_result.english_word,
            "search_query": translation_result.search_query,
            "media_reused": False,
        }

    except Exception as e:
        context = {
            "source_word": source_word,
            "target_word": target_word,
            "source_language": source_language,
            "target_language": target_language,
        }
        return create_tool_error_response(e, context)
