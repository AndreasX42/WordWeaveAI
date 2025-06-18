from aws_lambda_powertools import Logger
from elevenlabs import VoiceSettings
from elevenlabs.client import AsyncElevenLabs
from langchain.tools import tool
from vocab_processor.constants import Language
from vocab_processor.tools.base_tool import create_tool_error_response
from vocab_processor.utils.s3_utils import generate_vocab_s3_paths, upload_stream_to_s3

logger = Logger(service="vocab-processor")


@tool
async def get_pronunciation(
    target_word: str,
    target_syllables: list[str],
    target_language: Language,
) -> str:
    """Generate pronunciation audio using ElevenLabs and upload directly to S3."""

    try:
        client = AsyncElevenLabs()
        voice_id = "94zOad0g7T7K4oa7zhDq"  # Mauricio
        model_id = "eleven_flash_v2_5"
        language_code = target_language.code

        # Generate S3 paths using centralized utility
        s3_paths = generate_vocab_s3_paths(target_language, target_word)
        audio_prefix = s3_paths["audio_prefix"]

        async def generate_and_upload_audio(text: str, filename: str) -> str:
            """Generate audio and upload directly to S3."""

            voice_settings = VoiceSettings(
                speed=0.7 if "syllables" in filename else 0.85,
                stability=0.9,
                similarity_boost=0.9,
                style=0.9,
                use_speaker_boost=True,
            )

            # Generate audio stream
            audio_generator = client.text_to_speech.convert(
                text=text,
                voice_id=voice_id,
                language_code=language_code,
                model_id=model_id,
                output_format="mp3_44100_128",
                voice_settings=voice_settings,
            )

            # Upload stream directly to S3
            s3_key = f"{audio_prefix}/{filename}"
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
                syllables_text, "syllables.mp3"
            )
            result["syllables"] = syllables_url

        logger.info(f"Audio files uploaded to S3: {audio_prefix}/")
        return str(result)

    except Exception as e:
        context = {
            "target_word": target_word,
            "target_syllables": target_syllables,
            "target_language": target_language,
        }
        error_response = create_tool_error_response(e, context)
        return str(error_response)
