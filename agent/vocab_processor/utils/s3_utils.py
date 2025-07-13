import asyncio
import os
from typing import Dict

import boto3
from aws_lambda_powertools import Logger

from vocab_processor.constants import Language
from vocab_processor.utils.core_utils import is_lambda_context

logger = Logger(service="vocab-processor")

S3_BUCKET = os.getenv("S3_MEDIA_BUCKET_NAME")

# Initialize S3 client with optimized configuration
s3_client = boto3.client(
    "s3",
    region_name=os.getenv("AWS_REGION", "us-east-1"),
    config=boto3.session.Config(
        max_pool_connections=50,  # Increase connection pool
        retries={"max_attempts": 3, "mode": "adaptive"},
    ),
)


def generate_safe_word_key(word: str, max_length: int = 20) -> str:
    """Generate a safe string for use in file paths from a word."""
    return "".join(c for c in word if c.isalnum())[:max_length]


def generate_vocab_s3_paths(
    target_language: Language, target_word: str
) -> Dict[str, str]:
    """
    Generate standardized S3 paths for vocabulary content.
    """
    safe_target = generate_safe_word_key(target_word)
    base_prefix = f"vocabs/{target_language.code}/{safe_target}"

    return {
        "base_prefix": base_prefix,
        "audio_prefix": f"{base_prefix}/audio",
        "image_prefix": f"{base_prefix}/images",
    }


def generate_english_image_s3_paths(english_word: str) -> Dict[str, str]:
    """
    Generate English-based S3 paths for images.
    All images are stored under vocabs/en/{english_word}/images/* regardless of source/target language.
    """
    safe_english = generate_safe_word_key(english_word)
    image_prefix = f"vocabs/en/{safe_english}/images"

    return {
        "image_prefix": image_prefix,
        "large2x_key": f"{image_prefix}/large2x.jpg",
        "large_key": f"{image_prefix}/large.jpg",
        "medium_key": f"{image_prefix}/medium.jpg",
    }


async def check_s3_object_exists(s3_key: str) -> bool:
    """
    Check if an S3 object exists.

    Returns:
        True if object exists, False otherwise
    """
    if not is_lambda_context():
        logger.info(f"Local dev mode: skipping S3 existence check for {s3_key}")
        return False

    try:
        await asyncio.to_thread(s3_client.head_object, Bucket=S3_BUCKET, Key=s3_key)
        return True
    except Exception as e:
        logger.error(f"Error checking S3 object existence: {e}")
        return False


def generate_s3_url(s3_key: str) -> str:
    """Generate S3 URL from key."""
    if not is_lambda_context():
        return f"https://mock-s3-bucket.local/{s3_key}"
    return f"https://{S3_BUCKET}.s3.amazonaws.com/{s3_key}"


async def upload_bytes_to_s3(data: bytes, s3_key: str, content_type: str) -> str:
    """
    Upload bytes directly to S3.
    In local development mode, returns a mock URL without performing actual upload.

    Returns:
        S3 URL or mock URL in local mode
    """
    if not is_lambda_context():
        logger.info(
            f"Local dev mode: skipping S3 upload for {s3_key} ({len(data)} bytes, {content_type})"
        )
        return f"https://mock-s3-bucket.local/{s3_key}"

    try:
        await asyncio.to_thread(
            s3_client.put_object,
            Bucket=S3_BUCKET,
            Key=s3_key,
            Body=data,
            ContentType=content_type,
        )

        return f"https://{S3_BUCKET}.s3.amazonaws.com/{s3_key}"
    except Exception as e:
        logger.error(f"Error uploading to S3: {e}")
        return f"Error uploading to S3: {str(e)}"


async def upload_stream_to_s3(data_stream, s3_key: str, content_type: str) -> str:
    """
    Upload streaming data directly to S3.
    In local development mode, returns a mock URL without performing actual upload.

    Returns:
        S3 URL or mock URL in local mode
    """
    if not is_lambda_context():
        logger.info(
            f"Local dev mode: skipping S3 stream upload for {s3_key} ({content_type})"
        )
        return f"https://mock-s3-bucket.local/{s3_key}"

    try:
        # Collect stream data
        chunks = []
        async for chunk in data_stream:
            chunks.append(chunk)

        # Combine chunks and upload
        data = b"".join(chunks)
        return await upload_bytes_to_s3(data, s3_key, content_type)

    except Exception as e:
        logger.error(f"Error uploading stream to S3: {e}")
        return f"Error uploading stream to S3: {str(e)}"
