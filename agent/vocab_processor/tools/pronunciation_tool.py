import asyncio
import os
import random
from typing import Optional

from aws_lambda_powertools import Logger
from elevenlabs import VoiceSettings
from elevenlabs.client import AsyncElevenLabs
from langchain.tools import tool
from pydantic import BaseModel, Field

from vocab_processor.constants import Language
from vocab_processor.tools.base_tool import create_tool_error_response
from vocab_processor.utils.s3_utils import (
    generate_vocab_s3_paths,
    is_lambda_context,
    upload_stream_to_s3,
)

logger = Logger(service="vocab-processor")

# Configuration constants
MAX_AUDIO_SIZE_MB = 5  # Maximum audio file size in MB
MAX_AUDIO_RETRIES = 3  # Maximum retry attempts for failed audio generation
AUDIO_TIMEOUT_SECONDS = 30  # Timeout for audio generation requests

# Voice configuration with environment variable support
VOICE_CONFIG = {
    "voice_id": os.getenv(
        "ELEVENLABS_VOICE_ID", "94zOad0g7T7K4oa7zhDq"
    ),  # Default: Mauricio
    "model_id": os.getenv("ELEVENLABS_MODEL_ID", "eleven_flash_v2_5"),
    "word_speed": float(os.getenv("ELEVENLABS_WORD_SPEED", "0.85")),
    "syllables_speed": float(os.getenv("ELEVENLABS_SYLLABLES_SPEED", "0.7")),
    "voice_settings": {
        "stability": float(os.getenv("ELEVENLABS_STABILITY", "0.9")),
        "similarity_boost": float(os.getenv("ELEVENLABS_SIMILARITY_BOOST", "0.9")),
        "style": float(os.getenv("ELEVENLABS_STYLE", "0.9")),
        "use_speaker_boost": os.getenv("ELEVENLABS_SPEAKER_BOOST", "true").lower()
        == "true",
    },
}


class Pronunciations(BaseModel):
    """Result of pronunciation generation with audio URLs."""

    audio: str = Field(..., description="Url to audio file for normal pronunciation")
    syllables: Optional[str] = Field(
        default=None,
        description="Url to audio file for syllables pronunciation if there is more than one syllable",
    )


async def generate_audio_with_retry(
    client: AsyncElevenLabs,
    text: str,
    voice_id: str,
    language_code: str,
    model_id: str,
    voice_settings: VoiceSettings,
    max_retries: int = MAX_AUDIO_RETRIES,
) -> any:
    """Generate audio with retry logic and exponential backoff."""

    for attempt in range(max_retries):
        try:
            # Generate audio stream with timeout
            async def generate_audio():
                audio_generator = client.text_to_speech.convert(
                    text=text,
                    voice_id=voice_id,
                    language_code=language_code,
                    model_id=model_id,
                    output_format="mp3_44100_128",
                    voice_settings=voice_settings,
                )

                # Validate audio size by collecting chunks
                chunks = []
                total_size = 0

                async for chunk in audio_generator:
                    chunks.append(chunk)
                    total_size += len(chunk)

                    # Check size limit during streaming
                    if total_size > MAX_AUDIO_SIZE_MB * 1024 * 1024:
                        raise RuntimeError(
                            f"Audio file too large: {total_size / (1024*1024):.2f}MB > {MAX_AUDIO_SIZE_MB}MB"
                        )

                return chunks

            # Apply timeout to audio generation
            chunks = await asyncio.wait_for(
                generate_audio(), timeout=AUDIO_TIMEOUT_SECONDS
            )

            # Validate audio quality
            if not validate_audio_quality(chunks, text):
                raise RuntimeError(f"Audio quality validation failed for text: {text}")

            # Return async generator that yields the collected chunks
            async def replay_chunks():
                for chunk in chunks:
                    yield chunk

            return replay_chunks()

        except asyncio.TimeoutError:
            error_msg = f"Audio generation timed out after {AUDIO_TIMEOUT_SECONDS}s"
            if attempt < max_retries - 1:
                delay = (2**attempt) + random.uniform(0, 1)
                logger.warning(
                    f"Audio generation attempt {attempt + 1} timed out, retrying in {delay:.2f}s"
                )
                await asyncio.sleep(delay)
            else:
                raise RuntimeError(error_msg)
        except Exception as e:
            if attempt < max_retries - 1:
                delay = (2**attempt) + random.uniform(
                    0, 1
                )  # Exponential backoff with jitter
                logger.warning(
                    f"Audio generation attempt {attempt + 1} failed: {str(e)}, retrying in {delay:.2f}s"
                )
                await asyncio.sleep(delay)
            else:
                raise e

    # Instead of raising an exception, return None to indicate fallback should be used
    logger.error(f"Max retries exceeded for audio generation - will use fallback")
    return None


def validate_audio_quality(chunks: list, text: str) -> bool:
    """Validate audio quality based on size and content."""
    total_size = sum(len(chunk) for chunk in chunks)

    # Audio file should be at least 1KB (very small files indicate errors)
    if total_size < 1024:
        logger.warning(f"Audio file too small: {total_size} bytes for text '{text}'")
        return False

    # Log audio size for monitoring
    size_kb = total_size / 1024
    logger.info(f"Generated audio: {size_kb:.2f}KB for text '{text[:50]}...'")

    return True


@tool
async def get_pronunciation(
    target_word: str,
    target_syllables: list[str],
    target_language: Language,
) -> Pronunciations:
    """Generate pronunciation audio using ElevenLabs and upload directly to S3."""

    try:
        client = AsyncElevenLabs()
        language_code = target_language.code

        # Generate S3 paths using centralized utility
        s3_paths = generate_vocab_s3_paths(target_language, target_word)
        audio_prefix = s3_paths["audio_prefix"]

        if not is_lambda_context():
            logger.info(
                f"Local dev mode: pronunciation audio will use mock URLs (not uploaded to S3)"
            )
            # Return mock URLs immediately in dev mode
            audio_url = f"https://mock-s3-bucket.local/{audio_prefix}/pronunciation.mp3"
            syllables_url = None
            if len(target_syllables) > 1:
                syllables_url = (
                    f"https://mock-s3-bucket.local/{audio_prefix}/syllables.mp3"
                )
            return Pronunciations(audio=audio_url, syllables=syllables_url)

        async def generate_and_upload_audio(
            text: str, filename: str, is_syllables: bool = False
        ) -> str:
            """Generate audio and upload directly to S3."""
            s3_key = f"{audio_prefix}/{filename}"

            if not is_lambda_context():
                return f"https://mock-s3-bucket.local/{s3_key}"

            # Only make real API calls in lambda context
            voice_settings = VoiceSettings(
                speed=(
                    VOICE_CONFIG["syllables_speed"]
                    if is_syllables
                    else VOICE_CONFIG["word_speed"]
                ),
                stability=VOICE_CONFIG["voice_settings"]["stability"],  # type: ignore
                similarity_boost=VOICE_CONFIG["voice_settings"]["similarity_boost"],  # type: ignore
                style=VOICE_CONFIG["voice_settings"]["style"],  # type: ignore
                use_speaker_boost=VOICE_CONFIG["voice_settings"]["use_speaker_boost"],  # type: ignore
            )

            # Generate audio stream with retry logic
            audio_generator = await generate_audio_with_retry(
                client=client,
                text=text,
                voice_id=VOICE_CONFIG["voice_id"],
                language_code=language_code,
                model_id=VOICE_CONFIG["model_id"],
                voice_settings=voice_settings,
            )

            # Check if generation failed and return fallback
            if audio_generator is None:
                logger.warning(
                    f"Audio generation failed for {text}, using fallback URL"
                )
                return f"ERROR: Audio generation failed for {text}, {filename}, {'text' if not is_syllables else 'syllables'}"

            # Upload stream directly to S3
            return await upload_stream_to_s3(audio_generator, s3_key, "audio/mpeg")

        # Always generate word pronunciation
        audio_url = await generate_and_upload_audio(
            target_word,
            "pronunciation.mp3",
        )

        # Generate syllables audio if provided and more than one syllable
        syllables_url = None
        if len(target_syllables) > 1:
            syllables_text = "\n\n".join(target_syllables)
            syllables_url = await generate_and_upload_audio(
                syllables_text, "syllables.mp3", is_syllables=True
            )

        if is_lambda_context():
            logger.info(
                f"Audio files uploaded to S3: {audio_prefix}/",
                audio_url=audio_url,
                syllables_url=syllables_url,
            )
        else:
            logger.info(
                f"Local dev mode: mock audio URLs generated for {audio_prefix}/"
            )

        return Pronunciations(audio=audio_url, syllables=syllables_url)

    except Exception as e:
        logger.error(f"Pronunciation tool failed: {str(e)}")
        context = {
            "target_word": target_word,
            "target_syllables": target_syllables,
            "target_language": target_language,
        }
        error_response = create_tool_error_response(e, context)
        # Return a Pronunciations object with error URLs
        return Pronunciations(audio=f"ERROR: {str(error_response)}", syllables=None)
