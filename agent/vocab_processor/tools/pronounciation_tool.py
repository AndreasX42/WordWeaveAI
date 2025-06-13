import asyncio
import os
from pathlib import Path

import aiofiles
from dotenv import load_dotenv
from elevenlabs import VoiceSettings, save
from elevenlabs.client import AsyncElevenLabs
from langchain.tools import tool

from vocab_processor.constants import Language

load_dotenv()

# Base download directory
DOWNLOAD_FOLDER = os.getenv("DOWNLOAD_FOLDER", "downloads")


async def get_word_directory(target_language: Language, target_word: str) -> Path:
    """Create a directory specific to the target language and word (async)."""
    safe_word = "".join(c for c in target_word if c.isalnum())[:20]
    word_dir = Path(DOWNLOAD_FOLDER) / f"{target_language.name.lower()}_{safe_word}"

    # Use asyncio.to_thread to make mkdir non-blocking
    await asyncio.to_thread(word_dir.mkdir, parents=True, exist_ok=True)
    return word_dir


@tool
async def get_pronunciation(
    target_word: str, target_syllables: list[str], target_language: Language
) -> str:
    """Generate pronunciation audio using ElevenLabs for a word and its syllables."""

    try:
        client = AsyncElevenLabs()
        voice_id = "94zOad0g7T7K4oa7zhDq"  # Mauricio
        model_id = "eleven_flash_v2_5"
        language_code = target_language.code

        # Create word-specific directory (async)
        word_dir = await get_word_directory(target_language, target_word)

        async def generate_audio_for_text(text: str, filename: str) -> str:
            """Helper function to generate audio for given text."""

            voice_settings = VoiceSettings(
                speed=0.7 if "syllables" in filename else 0.85,
                stability=0.9,
                similarity_boost=0.9,
                style=0.9,
                use_speaker_boost=True,
            )

            audio_generator = client.text_to_speech.convert(
                text=text,
                voice_id=voice_id,
                language_code=language_code,
                model_id=model_id,
                output_format="mp3_44100_128",
                voice_settings=voice_settings,
            )

            # Collect all audio chunks
            audio_chunks = []
            async for chunk in audio_generator:
                audio_chunks.append(chunk)

            # Combine chunks into bytes
            audio_bytes = b"".join(audio_chunks)

            # Save file to word-specific directory
            file_path = word_dir / filename
            async with aiofiles.open(file_path, "wb") as f:
                await f.write(audio_bytes)

            return str(file_path)

        # Generate normal pronunciation
        audio_file = await generate_audio_for_text(target_word, "pronunciation.mp3")

        # Make abspath calls async to avoid blocking os.getcwd()
        audio_abspath = await asyncio.to_thread(os.path.abspath, audio_file)

        # Return file paths as JSON-like string
        result = {
            "audio": f"file://{audio_abspath}",
        }

        if len(target_syllables) > 0:
            syllables_file = await generate_audio_for_text(
                "\n\n".join(target_syllables), "syllables.mp3"
            )
            syllables_abspath = await asyncio.to_thread(os.path.abspath, syllables_file)
            result["syllables"] = f"file://{syllables_abspath}"

        print(f"Audio files downloaded to: {word_dir}/")
        return str(result)

    except Exception as e:
        print(f"Error generating audio: {e}")
        return f"Error generating audio: {e}"
