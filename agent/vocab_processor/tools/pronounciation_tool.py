from typing import Dict, Optional

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


class PronunciationResult(BaseModel):
    """Result of pronunciation generation with audio URLs."""

    pronunciations: Dict[str, str] = Field(
        ..., description="Dictionary containing pronunciation audio URLs"
    )


# Voice configuration
VOICE_CONFIG = {
    "voice_id": "94zOad0g7T7K4oa7zhDq",  # Mauricio
    "model_id": "eleven_flash_v2_5",
    "word_speed": 0.85,
    "syllables_speed": 0.7,
    "voice_settings": {
        "stability": 0.9,
        "similarity_boost": 0.9,
        "style": 0.9,
        "use_speaker_boost": True,
    },
}


@tool
async def get_pronunciation(
    target_word: str,
    target_syllables: list[str],
    target_language: Language,
) -> PronunciationResult:
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

        async def generate_and_upload_audio(
            text: str, filename: str, is_syllables: bool = False
        ) -> str:
            """Generate audio and upload directly to S3."""
            s3_key = f"{audio_prefix}/{filename}"

            if not is_lambda_context():
                return f"https://mock-s3-bucket.local/{s3_key}"

            voice_settings = VoiceSettings(
                speed=(
                    VOICE_CONFIG["syllables_speed"]
                    if is_syllables
                    else VOICE_CONFIG["word_speed"]
                ),
                stability=VOICE_CONFIG["voice_settings"]["stability"],
                similarity_boost=VOICE_CONFIG["voice_settings"]["similarity_boost"],
                style=VOICE_CONFIG["voice_settings"]["style"],
                use_speaker_boost=VOICE_CONFIG["voice_settings"]["use_speaker_boost"],
            )

            # Generate audio stream
            audio_generator = client.text_to_speech.convert(
                text=text,
                voice_id=VOICE_CONFIG["voice_id"],
                language_code=language_code,
                model_id=VOICE_CONFIG["model_id"],
                output_format="mp3_44100_128",
                voice_settings=voice_settings,
            )

            # Upload stream directly to S3
            return await upload_stream_to_s3(audio_generator, s3_key, "audio/mpeg")

        # Generate pronunciation audio
        audio_url = await generate_and_upload_audio(target_word, "pronunciation.mp3")

        result = {
            "audio": audio_url,
        }

        # Generate syllable audio if provided
        if len(target_syllables) > 0:
            syllables_text = "\n\n".join(target_syllables)
            syllables_url = await generate_and_upload_audio(
                syllables_text, "syllables.mp3", is_syllables=True
            )
            result["syllables"] = syllables_url

        if is_lambda_context():
            logger.info(f"Audio files uploaded to S3: {audio_prefix}/")
        else:
            logger.info(
                f"Local dev mode: mock audio URLs generated for {audio_prefix}/"
            )

        return PronunciationResult(pronunciations=result)

    except Exception as e:
        context = {
            "target_word": target_word,
            "target_syllables": target_syllables,
            "target_language": target_language,
        }
        error_response = create_tool_error_response(e, context)
        return PronunciationResult(pronunciations={"error": str(error_response)})
