from langchain.tools import tool
from my_agent.constants import Language
from elevenlabs import VoiceSettings, save
from elevenlabs.client import AsyncElevenLabs
from dotenv import load_dotenv
import aiofiles

load_dotenv()

@tool
async def get_pronunciation(target_word: str, target_syllables: list[str], target_language: Language) -> str:
    """Generate pronunciation audio using ElevenLabs for a word and its syllables with pauses."""
    
    try:
        client = AsyncElevenLabs()
        voice_id = "94zOad0g7T7K4oa7zhDq"  # Mauricio
        model_id = "eleven_flash_v2_5"
        language_code = target_language.code
        
        async def generate_audio_for_text(text: str, filename_suffix: str = None) -> str:
            """Helper function to generate audio for given text."""
            
            voice_settings = VoiceSettings(
                speed=0.7 if filename_suffix else 0.85,
                stability=0.9,
                similarity_boost=0.9,
                style=0.9,
                use_speaker_boost=True
            )
            
            audio_generator = client.text_to_speech.convert(
                text=text,
                voice_id=voice_id,
                language_code=language_code,
                model_id=model_id,
                output_format="mp3_44100_128",
                voice_settings=voice_settings
            )
            
            # Collect all audio chunks
            audio_chunks = []
            async for chunk in audio_generator:
                audio_chunks.append(chunk)
            
            # Combine chunks into bytes
            audio_bytes = b"".join(audio_chunks)
            
            # Save file
            filename = f"{language_code}_{target_word}_{filename_suffix}.mp3" if filename_suffix else f"{language_code}_{target_word}.mp3"
            async with aiofiles.open(filename, "wb") as f:
                await f.write(audio_bytes)
            
            return filename
        
        # Generate normal pronunciation
        audio_file = await generate_audio_for_text(target_word)
        
        # Generate syllable pronunciation with pauses (newlines create pauses)
        syllables_file = await generate_audio_for_text("\n".join(target_syllables), "syllables")
        
        # Return both file paths as JSON-like string
        result = {
            "audio": f"file://{audio_file}",
            "syllables": f"file://{syllables_file}",
        }
        
        return str(result)
        
    except Exception as e:
        print(f"Error generating audio: {e}")
        return f"Error generating audio: {e}"