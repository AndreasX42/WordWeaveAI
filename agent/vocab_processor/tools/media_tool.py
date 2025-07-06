import os
from typing import Any, List, Optional

import aiohttp
from aws_lambda_powertools import Logger
from langchain.tools import tool
from pydantic import BaseModel, Field

from vocab_processor.constants import Language
from vocab_processor.schemas.media_model import Media, PhotoOption
from vocab_processor.tools.base_tool import (
    SystemMessages,
    add_quality_feedback_to_prompt,
    create_llm_response,
    create_tool_error_response,
)
from vocab_processor.utils.ddb_utils import get_existing_media_for_search_words
from vocab_processor.utils.s3_utils import (
    generate_english_image_s3_paths,
    is_lambda_context,
    upload_bytes_to_s3,
)

logger = Logger(service="vocab-processor")

# Configuration constants
PEXELS_API_KEY = os.getenv("PEXELS_API_KEY")
PEXELS_PHOTO_SEARCH_URL = "https://api.pexels.com/v1/search"
HTTP_TIMEOUT = 30
PHOTOS_PER_PAGE = 10

# HTTP session configuration
_session_config = aiohttp.ClientTimeout(total=HTTP_TIMEOUT, connect=5)


class TranslationResult(BaseModel):
    english_word: str = Field(
        description="The English translation of the target word including article if it is a proper noun or 'to' if it is a verb"
    )
    search_query: list[str] = Field(
        description="English search query plus 2 or 3 descriptive synonyms to find the most relevant photos in Pexels",
        min_length=2,
        max_length=3,
    )


async def fetch_photos(query: str | list[str], per_page: int = 3) -> list[PhotoOption]:
    """Fetch photos from Pexels API."""
    # Convert list to space-separated string for Pexels API
    search_query = " ".join(query) if isinstance(query, list) else query

    # In local dev mode, return mock data instead of making real API calls
    if not is_lambda_context():
        logger.info(
            f"Local dev mode: returning mock photos for query '{search_query}' (per_page={per_page})"
        )
        return _create_mock_photos(search_query, per_page)

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

            # Clean up photo data structure
            for photo in photos_data:
                photo["src"] = {
                    "large2x": photo["src"]["large2x"],
                    "small": photo["src"]["small"],
                }

            return [PhotoOption(**photo) for photo in photos_data]


def _create_mock_photos(search_query: str, per_page: int) -> list[PhotoOption]:
    """Create mock photos for local development."""
    mock_photos = []
    for i in range(min(per_page, 3)):
        mock_photo = {
            "id": f"mock_photo_{i+1}",
            "width": 4000,
            "height": 3000,
            "url": f"https://mock-pexels.local/photo/{i+1}",
            "photographer": "Mock Photographer",
            "photographer_url": "https://mock-pexels.local/photographer",
            "photographer_id": 12345,
            "avg_color": "#8B7355",
            "src": {
                "large2x": f"https://mock-pexels.local/photo/{i+1}_large2x.jpg",
                "small": f"https://mock-pexels.local/photo/{i+1}_small.jpg",
            },
            "liked": False,
            "alt": f"Mock photo {i+1} for {search_query}",
        }
        mock_photos.append(mock_photo)
    return [PhotoOption(**photo) for photo in mock_photos]


async def upload_to_s3(url: str, s3_key: str) -> str:
    """Download image from URL and upload directly to S3."""
    try:
        if not is_lambda_context():
            logger.info(
                f"Local dev mode: skipping image download and S3 upload for {s3_key}"
            )
            return f"https://mock-s3-bucket.local/{s3_key}"

        async with aiohttp.ClientSession(timeout=_session_config) as session:
            async with session.get(url) as response:
                if response.status == 200:
                    # Read image data and upload directly to S3
                    image_data = await response.read()
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
    quality_feedback: Optional[str] = None,
    previous_issues: Optional[List[str]] = None,
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
        translation_prompt = f"For '{target_word}' ({target_language}): provide english_word + 2-3 descriptive English search terms."

        translation_result = await create_llm_response(
            response_model=TranslationResult,
            user_prompt=translation_prompt,
        )

        # Check if we already have Media object for any similar search words
        existing_media = await get_existing_media_for_search_words(
            translation_result.search_query
        )
        if existing_media:
            return await _adapt_existing_media(
                existing_media,
                source_word,
                target_word,
                source_language,
                target_language,
                translation_result,
            )

        # If no database entry, fetch from Pexels API
        return await _create_new_media(
            source_word,
            target_word,
            source_language,
            target_language,
            translation_result,
            quality_feedback,
            previous_issues,
        )

    except Exception as e:
        context = {
            "source_word": source_word,
            "target_word": target_word,
            "source_language": source_language,
            "target_language": target_language,
        }
        return create_tool_error_response(e, context)


async def _adapt_existing_media(
    existing_media: dict,
    source_word: str,
    target_word: str,
    source_language: Language,
    target_language: Language,
    translation_result: TranslationResult,
) -> dict[str, Any]:
    """Adapt existing media for the current word."""
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


async def _create_new_media(
    source_word: str,
    target_word: str,
    source_language: Language,
    target_language: Language,
    translation_result: TranslationResult,
    quality_feedback: Optional[str] = None,
    previous_issues: Optional[List[str]] = None,
) -> dict[str, Any]:
    """Create new media by fetching from Pexels API."""
    image_paths = generate_english_image_s3_paths(translation_result.english_word)
    large_key = image_paths["large_key"]
    small_key = image_paths["small_key"]

    logger.info(
        f"No existing Media found for search words {translation_result.search_query}, fetching from Pexels"
    )

    if not is_lambda_context():
        logger.info("Local dev mode: images will use mock URLs (not uploaded to S3)")

    photos = await fetch_photos(
        translation_result.search_query, per_page=PHOTOS_PER_PAGE
    )

    if not photos:
        return {
            "media": Media(
                url="",
                alt="No photos found matching the query.",
                src={"large2x": "", "small": ""},
                explanation="No suitable images were found for this word.",
                memory_tip="Try visualizing the word concept in your mind.",
            ),
            "english_word": translation_result.english_word,
            "search_query": translation_result.search_query,
            "media_reused": False,
        }

    # Select the best photo
    if not is_lambda_context():
        # In dev mode, just use the first photo
        logger.info("Local dev mode: using first photo without LLM selection")
        result_media = _create_mock_media(photos[0], target_word)
    else:
        # In lambda context, use LLM to choose the best photo
        result_media = await _select_best_photo(
            photos,
            source_word,
            target_word,
            source_language,
            target_language,
            quality_feedback,
            previous_issues,
        )

    # Upload images to S3
    await _upload_media_to_s3(result_media, large_key, small_key, image_paths)

    return {
        "media": result_media,
        "english_word": translation_result.english_word,
        "search_query": translation_result.search_query,
        "media_reused": False,
    }


def _create_mock_media(photo: PhotoOption, target_word: str) -> Media:
    """Create mock media for local development."""
    return Media(
        url=photo.url,
        alt=f"Mock image for {target_word}",
        src={
            "large2x": photo.src["large2x"],
            "small": photo.src["small"],
        },
        explanation=f"This is a mock image for the word '{target_word}'.",
        memory_tip=f"Remember '{target_word}' by visualizing this image.",
    )


async def _select_best_photo(
    photos: List[PhotoOption],
    source_word: str,
    target_word: str,
    source_language: Language,
    target_language: Language,
    quality_feedback: Optional[str] = None,
    previous_issues: Optional[List[str]] = None,
) -> Media:
    """Use LLM to select the best photo from the available options."""
    rank_prompt = f"Choose best photo for '{source_word}' ({source_language}) → '{target_word}' ({target_language}). Translate the texts like in alt, explanation, memory_tip to the source language {source_language}. Photos: {[p.model_dump() for p in photos]}"

    # Quality requirements for media selection
    quality_requirements = [
        "Choose relevant, clear photo",
        f"Accurate {source_language} translations",
        "Connect image to word in memory tip",
        "Clear explanations",
        "Culturally appropriate",
    ]

    # Add quality feedback if provided
    enhanced_prompt = add_quality_feedback_to_prompt(
        rank_prompt, quality_feedback, previous_issues, quality_requirements
    )

    return await create_llm_response(
        response_model=Media,
        user_prompt=enhanced_prompt,
        system_message=SystemMessages.MEDIA_SPECIALIST,
    )


async def _upload_media_to_s3(
    result_media: Media,
    large_key: str,
    small_key: str,
    image_paths: dict,
) -> None:
    """Upload media images to S3."""
    if not result_media.src or not isinstance(result_media.src, dict):
        logger.info("No valid src data for S3 upload")
        return

    # Clean up any None keys or values in src dict
    cleaned_src = {
        k: v for k, v in result_media.src.items() if k is not None and v is not None
    }

    if not cleaned_src.get("large2x") or not cleaned_src.get("small"):
        logger.info("Invalid src URLs for S3 upload")
        return

    try:
        # Download and upload both versions directly to S3 using English-based paths
        large_s3_url = await upload_to_s3(cleaned_src["large2x"], large_key)
        small_s3_url = await upload_to_s3(cleaned_src["small"], small_key)

        # Update URLs if uploads were successful
        if not large_s3_url.startswith("Error") and not small_s3_url.startswith(
            "Error"
        ):
            result_media.src = {
                "large2x": large_s3_url,
                "small": small_s3_url,
            }
            if is_lambda_context():
                logger.info(f"Images uploaded to S3: {image_paths['image_prefix']}/")
            else:
                logger.info(
                    f"Local dev mode: mock image URLs generated for {image_paths['image_prefix']}/"
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
