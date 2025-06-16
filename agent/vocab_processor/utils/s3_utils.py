import asyncio
import os
import uuid
from typing import Dict

import boto3
from vocab_processor.constants import Language

S3_BUCKET = os.getenv("S3_MEDIA_BUCKET")

# Initialize S3 client
s3_client = boto3.client("s3")


def generate_safe_word_key(word: str, max_length: int = 20) -> str:
    """Generate a safe string for use in file paths from a word."""
    return "".join(c for c in word if c.isalnum())[:max_length]


def generate_vocab_s3_paths(
    target_language: Language, target_word: str
) -> Dict[str, str]:
    """
    Generate standardized S3 paths for vocabulary content.

    Returns:
        Dict with keys: 'base_prefix', 'audio_prefix', 'image_prefix'
    """
    safe_target = generate_safe_word_key(target_word)
    base_prefix = f"vocabs/{target_language.code}/{safe_target}"

    return {
        "base_prefix": base_prefix,
        "audio_prefix": f"{base_prefix}/audio",
        "image_prefix": f"{base_prefix}/images",
    }


async def upload_bytes_to_s3(data: bytes, s3_key: str, content_type: str) -> str:
    """
    Upload bytes directly to S3 without local storage.

    Returns:
        S3 URL or error message
    """
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
        print(f"Error uploading to S3: {e}")
        return f"Error uploading to S3: {str(e)}"


async def upload_stream_to_s3(data_stream, s3_key: str, content_type: str) -> str:
    """
    Upload streaming data directly to S3.

    Returns:
        S3 URL or error message
    """
    try:
        # Collect stream data
        chunks = []
        async for chunk in data_stream:
            chunks.append(chunk)

        # Combine chunks and upload
        data = b"".join(chunks)
        return await upload_bytes_to_s3(data, s3_key, content_type)

    except Exception as e:
        print(f"Error uploading stream to S3: {e}")
        return f"Error uploading stream to S3: {str(e)}"
