import asyncio
import os
import random
from typing import Any, Optional

import aiohttp
from aws_lambda_powertools import Logger
from langchain.tools import tool

from vocab_processor.constants import Language
from vocab_processor.prompts import (
    MEDIA_SEARCH_QUERY_PROMPT_TEMPLATE,
    MEDIA_SELECTION_PROMPT_TEMPLATE,
)
from vocab_processor.schemas.media_model import Media, PhotoOption, SearchQueryResult
from vocab_processor.tools.base_tool import (
    SystemMessages,
    create_llm_response,
    create_tool_error_response,
)
from vocab_processor.utils.ddb_utils import (
    get_existing_media_for_search_words,
    lang_code,
    normalize_word,
)
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

# S3 Upload configuration
MAX_IMAGE_SIZE_MB = 5
MAX_UPLOAD_RETRIES = 3

# HTTP session configuration
_session_config = aiohttp.ClientTimeout(total=HTTP_TIMEOUT, connect=5)


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
                    "large": photo["src"]["large"],
                    "medium": photo["src"]["medium"],
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
                "large": f"https://mock-pexels.local/photo/{i+1}_large.jpg",
                "medium": f"https://mock-pexels.local/photo/{i+1}_medium.jpg",
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
                    # Get content length for size validation
                    content_length = response.headers.get("content-length")

                    if content_length:
                        size_mb = int(content_length) / (1024 * 1024)

                        # Validate image size before download
                        if size_mb > MAX_IMAGE_SIZE_MB:
                            logger.warning(
                                f"Image too large: {s3_key} ({size_mb:.2f}MB > {MAX_IMAGE_SIZE_MB}MB)"
                            )
                            return f"Error: Image too large ({size_mb:.2f}MB)"

                    # Download image data
                    image_data = await response.read()

                    # Validate size after download (fallback if no content-length header)
                    if not content_length:
                        size_mb = len(image_data) / (1024 * 1024)
                        if size_mb > MAX_IMAGE_SIZE_MB:
                            logger.warning(
                                f"Downloaded image too large: {s3_key} ({size_mb:.2f}MB > {MAX_IMAGE_SIZE_MB}MB)"
                            )
                            return (
                                f"Error: Downloaded image too large ({size_mb:.2f}MB)"
                            )

                    return await upload_bytes_to_s3(image_data, s3_key, "image/jpeg")
                else:
                    raise RuntimeError(
                        f"Failed to download image: HTTP {response.status}"
                    )
    except Exception as e:
        logger.error("image_download_failed", url=url, s3_key=s3_key, error=str(e))
        return f"Error: {str(e)}"


async def upload_to_s3_with_retry(
    url: str, s3_key: str, max_retries: int = MAX_UPLOAD_RETRIES
) -> str:
    """Upload to S3 with retry logic and exponential backoff."""
    for attempt in range(max_retries):
        try:
            result = await upload_to_s3(url, s3_key)
            if not result.startswith("Error"):
                return result

            # If we get an error result, treat it as a failed attempt
            if attempt < max_retries - 1:
                delay = (2**attempt) + random.uniform(
                    0, 1
                )  # Exponential backoff with jitter
                logger.warning(
                    f"Upload attempt {attempt + 1} failed for {s3_key}, retrying in {delay:.2f}s"
                )
                await asyncio.sleep(delay)
            else:
                return result

        except Exception as e:
            if attempt < max_retries - 1:
                delay = (2**attempt) + random.uniform(0, 1)
                logger.warning(
                    f"Upload attempt {attempt + 1} failed for {s3_key}: {str(e)}, retrying in {delay:.2f}s"
                )
                await asyncio.sleep(delay)
            else:
                return f"Error: {str(e)}"

    return f"Error: Max retries exceeded for {s3_key}"


@tool
async def get_media(
    source_word: str,
    target_word: str,
    english_word: str,
    source_language: Language,
    target_language: Language,
    source_definition: Optional[list[str]] = None,
    target_additional_info: Optional[str] = None,
    quality_feedback: Optional[str] = None,
    previous_issues: Optional[list[str]] = None,
    suggestions: Optional[list[str]] = None,
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
        context_info = ""
        if source_definition:
            context_info += f"\nSource word definition: {', '.join(source_definition)}"
        if target_additional_info:
            context_info += f"\nAdditional context: {target_additional_info}"

        search_query_prompt = MEDIA_SEARCH_QUERY_PROMPT_TEMPLATE.build_enhanced_prompt(
            english_word=english_word,
            context_info=context_info,
            quality_feedback=quality_feedback,
            previous_issues=previous_issues,
            suggestions=suggestions,
        )

        search_query_result = await create_llm_response(
            response_model=SearchQueryResult,
            user_prompt=search_query_prompt,
        )

        logger.info(
            f"Generated search terms for '{english_word}': {search_query_result.search_query}"
        )

        # Check if we already have Media object for any similar search words
        existing_media = await get_existing_media_for_search_words(
            search_query_result.search_query
        )
        if existing_media:
            result = await _adapt_existing_media(
                existing_media,
                source_word,
                target_word,
                english_word,
                source_language,
                target_language,
                search_query_result,
            )

            if result:
                result_dict = {**result, "search_query_prompt": search_query_prompt}
                if "media_selection_prompt" not in result_dict:
                    result_dict["media_selection_prompt"] = None
                return result_dict

        # If no existing media, create new media
        result = await _create_new_media(
            source_word,
            target_word,
            english_word,
            source_language,
            target_language,
            search_query_result,
            quality_feedback,
            previous_issues,
            suggestions,
        )

        return {**result, "search_query_prompt": search_query_prompt}

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
    english_word: str,
    source_language: Language,
    target_language: Language,
    search_query_result: SearchQueryResult,
) -> dict[str, Any]:
    """Adapt existing media for the current word."""
    matched_word = existing_media.get("matched_word", "unknown")
    requested_lang = lang_code(source_language)

    logger.info(
        f"Found existing Media object for search word '{matched_word}' (from query {search_query_result.search_query})"
    )

    # Check if existing media is already in the requested language
    existing_media_ref = existing_media.get("media_ref")
    if existing_media_ref and existing_media_ref.startswith("MEDIA#"):
        # Parse media_ref format: MEDIA#{lang}#{word} or MEDIA#{lang}#{word}#{hash}
        parts = existing_media_ref.split("#")
        if len(parts) >= 3:
            existing_lang = parts[1]  # Second part is the language code

            if existing_lang == requested_lang:
                logger.info(
                    f"Media already in requested language ({requested_lang}), returning as-is with existing media_ref: {existing_media_ref}"
                )
                # Return existing media directly without adaptation
                return {
                    "media": existing_media,
                    "media_ref": existing_media_ref,
                    "english_word": english_word,
                    "search_query": search_query_result.search_query,
                    "media_reused": True,
                    "media_adapted": False,  # No adaptation needed
                }

    # If we get here, the media needs to be adapted to the new language
    logger.info(f"Adapting media from existing language to {requested_lang}")

    # Pass raw DDB media data to LLM for translation and formatting
    adaptation_prompt = f"""Convert this existing media data to a Media object with texts translated to {source_language} for '{source_word}' ({source_language}) → '{target_word}' ({target_language}).

Existing media data: {existing_media}

Translate alt, explanation, and memory_tip to {source_language}. Keep url and src unchanged."""

    media = await create_llm_response(
        response_model=Media,
        user_prompt=adaptation_prompt,
        system_message=SystemMessages.MEDIA_SPECIALIST,
    )

    # Generate consistent media reference based on search terms (not specific word)
    search_terms_key = "_".join(
        sorted([normalize_word(term) for term in search_query_result.search_query])
    )
    media_ref = f"MEDIA#{requested_lang}#{search_terms_key}"

    logger.info(
        f"Generated new media_ref for adapted media: {media_ref} from search terms: {search_query_result.search_query}"
    )

    return {
        "media": media,
        "media_ref": media_ref,
        "english_word": english_word,
        "search_query": search_query_result.search_query,
        "media_reused": True,
        "media_adapted": True,
    }


async def _create_new_media(
    source_word: str,
    target_word: str,
    english_word: str,
    source_language: Language,
    target_language: Language,
    search_query_result: SearchQueryResult,
    quality_feedback: Optional[str] = None,
    previous_issues: Optional[list[str]] = None,
    suggestions: Optional[list[str]] = None,
) -> dict[str, Any]:
    """Create new media by fetching from Pexels API."""
    image_paths = generate_english_image_s3_paths(english_word)

    logger.info(
        f"No existing Media found for search words {english_word}, fetching from Pexels"
    )

    if not is_lambda_context():
        logger.info("Local dev mode: images will use mock URLs (not uploaded to S3)")

    photos = await fetch_photos(
        search_query_result.search_query, per_page=PHOTOS_PER_PAGE
    )

    if not photos:
        return {
            "media": Media(
                url="",
                alt="No photos found matching the query.",
                src={"large2x": "", "large": "", "medium": ""},
                explanation="No suitable images were found for this word.",
                memory_tip="Try visualizing the word concept in your mind.",
            ),
            "english_word": english_word,
            "search_query": search_query_result.search_query,
            "media_reused": False,
            "media_selection_prompt": None,
        }

    # Select the best photo
    if not is_lambda_context():
        # In dev mode, just use the first photo
        logger.info("Local dev mode: using first photo without LLM selection")
        result_media = _create_mock_media(photos[0], target_word)
        media_selection_prompt = "mock_prompt"
    else:
        # In lambda context, use LLM to choose the best photo
        result_media, media_selection_prompt = await _select_best_photo(
            photos,
            source_word,
            target_word,
            source_language,
            target_language,
            quality_feedback,
            previous_issues,
            suggestions,
        )

    # Upload images to S3
    await _upload_media_to_s3(result_media, image_paths)

    # Generate consistent media reference based on search terms (not specific word)
    search_terms_key = "_".join(
        sorted([normalize_word(term) for term in search_query_result.search_query])
    )
    media_ref = f"MEDIA#{lang_code(source_language)}#{search_terms_key}"

    logger.info(
        f"Generated new media_ref for new media: {media_ref} from search terms: {search_query_result.search_query}"
    )

    return {
        "media": result_media,
        "media_ref": media_ref,
        "english_word": english_word,
        "search_query": search_query_result.search_query,
        "media_reused": False,
        "media_selection_prompt": media_selection_prompt,
    }


def _create_mock_media(photo: PhotoOption, target_word: str) -> Media:
    """Create mock media for local development."""
    return Media(
        url=photo.url,
        alt=f"Mock image for {target_word}",
        src={
            "large2x": photo.src["large2x"],
            "large": photo.src["large"],
            "medium": photo.src["medium"],
        },
        explanation=f"This is a mock image for the word '{target_word}'.",
        memory_tip=f"Remember '{target_word}' by visualizing this image.",
    )


async def _select_best_photo(
    photos: list[PhotoOption],
    source_word: str,
    target_word: str,
    source_language: Language,
    target_language: Language,
    quality_feedback: Optional[str] = None,
    previous_issues: Optional[list[str]] = None,
    suggestions: Optional[list[str]] = None,
) -> tuple[Media, str]:
    """Use LLM to select the best photo from the available options."""

    enhanced_prompt = MEDIA_SELECTION_PROMPT_TEMPLATE.build_enhanced_prompt(
        quality_feedback=quality_feedback,
        previous_issues=previous_issues,
        suggestions=suggestions,
        source_word=source_word,
        source_language=source_language.value,
        target_word=target_word,
        target_language=target_language.value,
        photos=[p.model_dump() for p in photos],
    )

    result = await create_llm_response(
        response_model=Media,
        user_prompt=enhanced_prompt,
        system_message=SystemMessages.MEDIA_SPECIALIST,
    )
    return result, enhanced_prompt


async def _upload_media_to_s3(
    result_media: Media,
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

    if (
        not cleaned_src.get("large2x")
        or not cleaned_src.get("large")
        or not cleaned_src.get("medium")
    ):
        logger.info("Invalid src URLs for S3 upload")
        return

    try:
        # Upload all image sizes in parallel
        upload_tasks = []
        size_mappings = [
            ("large2x", "large2x_key"),
            ("large", "large_key"),
            ("medium", "medium_key"),
        ]

        for size_name, key_name in size_mappings:
            if cleaned_src.get(size_name) and image_paths.get(key_name):
                upload_tasks.append(
                    upload_to_s3_with_retry(
                        cleaned_src[size_name], image_paths[key_name]
                    )
                )

        # Execute all uploads concurrently
        upload_results = await asyncio.gather(*upload_tasks, return_exceptions=True)

        # Process results and update URLs
        successful_uploads = {}
        failed_uploads = []

        for i, (size_name, key_name) in enumerate(size_mappings):
            if i < len(upload_results):
                result = upload_results[i]
                if isinstance(result, Exception):
                    failed_uploads.append((size_name, str(result)))
                    logger.error(f"S3_upload_failed_{size_name}", error=str(result))
                elif not result.startswith("Error"):
                    successful_uploads[size_name] = result
                else:
                    failed_uploads.append((size_name, result))

        # Update URLs only for successful uploads
        if successful_uploads:
            updated_src = {}
            for size_name, _ in size_mappings:
                if size_name in successful_uploads:
                    updated_src[size_name] = successful_uploads[size_name]
                else:
                    # Keep original URL if upload failed
                    updated_src[size_name] = cleaned_src.get(size_name, "")

            result_media.src = updated_src

            if is_lambda_context():
                logger.info(
                    f"Images uploaded to S3: {image_paths['image_prefix']}/",
                    successful_count=len(successful_uploads),
                    failed_count=len(failed_uploads),
                )
            else:
                logger.info(
                    f"Local dev mode: mock image URLs generated for {image_paths['image_prefix']}/"
                )
        else:
            logger.warning("All S3 uploads failed, keeping original URLs")

    except Exception as e:
        logger.error(
            "S3_upload_failed",
            url=cleaned_src["large2x"],
            s3_key=image_paths["large2x_key"],
            error=str(e),
        )
