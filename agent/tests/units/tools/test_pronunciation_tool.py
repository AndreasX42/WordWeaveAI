from unittest.mock import MagicMock, patch

import pytest

from vocab_processor.constants import Language
from vocab_processor.tools.pronunciation_tool import Pronunciations, get_pronunciation


@pytest.mark.anyio
@patch("vocab_processor.tools.pronunciation_tool.is_lambda_context", return_value=False)
async def test_get_pronunciation_local_context(mock_is_lambda_context):
    # Arrange
    target_word = "hello"
    target_syllables = ["hel", "lo"]
    target_language = Language.ENGLISH

    # Act
    response = await get_pronunciation.ainvoke(
        {
            "target_word": target_word,
            "target_syllables": target_syllables,
            "target_language": target_language,
        }
    )

    # Assert
    assert isinstance(response, Pronunciations)
    # The tool should return mock URLs for local dev mode
    assert response.audio.startswith("https://mock-s3-bucket.local/")
    assert response.syllables.startswith("https://mock-s3-bucket.local/")
    mock_is_lambda_context.assert_called()


@pytest.mark.anyio
@patch("vocab_processor.tools.pronunciation_tool.is_lambda_context", return_value=False)
@patch("vocab_processor.tools.pronunciation_tool.generate_vocab_s3_paths")
async def test_get_pronunciation_lambda_context(
    mock_generate_s3_paths, mock_is_lambda_context
):
    # Arrange
    target_word = "hello"
    target_syllables = ["hel", "lo"]
    target_language = Language.ENGLISH

    # Mock S3 paths
    mock_generate_s3_paths.return_value = {"audio_prefix": "vocabs/en/hello/audio"}

    # Act
    response = await get_pronunciation.ainvoke(
        {
            "target_word": target_word,
            "target_syllables": target_syllables,
            "target_language": target_language,
        }
    )

    # Assert
    assert isinstance(response, Pronunciations)
    assert response.audio.startswith("https://mock-s3-bucket.local/")
    assert response.syllables.startswith("https://mock-s3-bucket.local/")
    mock_is_lambda_context.assert_called()


@pytest.mark.anyio
@patch("vocab_processor.tools.pronunciation_tool.is_lambda_context", return_value=True)
@patch("vocab_processor.tools.pronunciation_tool.boto3")
@patch("vocab_processor.tools.pronunciation_tool.generate_vocab_s3_paths")
@patch("os.getenv")
async def test_get_pronunciation_reuse_existing_files(
    mock_getenv, mock_generate_s3_paths, mock_boto3, mock_is_lambda_context
):
    # Arrange
    target_word = "hello"
    target_syllables = ["hel", "lo"]
    target_language = Language.ENGLISH

    # Mock environment and S3 paths
    mock_getenv.return_value = "test-bucket"
    mock_generate_s3_paths.return_value = {"audio_prefix": "vocabs/en/hello/audio"}

    # Mock S3 client to simulate existing files
    mock_s3_client = MagicMock()
    mock_boto3.client.return_value = mock_s3_client
    mock_s3_client.head_object.return_value = {}  # File exists

    # Act
    response = await get_pronunciation.ainvoke(
        {
            "target_word": target_word,
            "target_syllables": target_syllables,
            "target_language": target_language,
        }
    )

    # Assert
    assert isinstance(response, Pronunciations)
    # Should return S3 URLs for existing files
    assert (
        response.audio
        == "https://test-bucket.s3.amazonaws.com/vocabs/en/hello/audio/pronunciation.mp3"
    )
    assert (
        response.syllables
        == "https://test-bucket.s3.amazonaws.com/vocabs/en/hello/audio/syllables.mp3"
    )

    # Should check for both files
    assert mock_s3_client.head_object.call_count == 2
    mock_s3_client.head_object.assert_any_call(
        Bucket="test-bucket", Key="vocabs/en/hello/audio/pronunciation.mp3"
    )
    mock_s3_client.head_object.assert_any_call(
        Bucket="test-bucket", Key="vocabs/en/hello/audio/syllables.mp3"
    )


@pytest.mark.anyio
@patch("vocab_processor.tools.pronunciation_tool.is_lambda_context", return_value=True)
@patch("vocab_processor.tools.pronunciation_tool.boto3")
@patch("vocab_processor.tools.pronunciation_tool.generate_vocab_s3_paths")
@patch("vocab_processor.tools.pronunciation_tool.AsyncElevenLabs")
@patch("vocab_processor.tools.pronunciation_tool.upload_stream_to_s3")
@patch("os.getenv")
async def test_get_pronunciation_generate_missing_files(
    mock_getenv,
    mock_upload_s3,
    mock_eleven_labs,
    mock_generate_s3_paths,
    mock_boto3,
    mock_is_lambda_context,
):
    # Arrange
    target_word = "hello"
    target_syllables = ["hel", "lo"]
    target_language = Language.ENGLISH

    # Mock environment and S3 paths
    mock_getenv.return_value = "test-bucket"
    mock_generate_s3_paths.return_value = {"audio_prefix": "vocabs/en/hello/audio"}

    # Mock S3 client to simulate no existing files
    mock_s3_client = MagicMock()
    mock_boto3.client.return_value = mock_s3_client
    mock_s3_client.head_object.side_effect = mock_s3_client.exceptions.NoSuchKey(
        "Not found"
    )
    mock_s3_client.exceptions.NoSuchKey = Exception

    # Mock ElevenLabs and upload
    mock_client = MagicMock()
    mock_eleven_labs.return_value = mock_client

    # Mock upload_stream_to_s3 to return URLs based on S3 key paths
    def mock_upload_side_effect(audio_generator, s3_key, content_type):
        return f"https://test-bucket.s3.amazonaws.com/{s3_key}"

    mock_upload_s3.side_effect = mock_upload_side_effect

    # Mock audio generation
    async def mock_audio_generator():
        yield b"mock_audio_data"

    with patch(
        "vocab_processor.tools.pronunciation_tool.generate_audio_with_retry",
        return_value=mock_audio_generator(),
    ):
        # Act
        response = await get_pronunciation.ainvoke(
            {
                "target_word": target_word,
                "target_syllables": target_syllables,
                "target_language": target_language,
            }
        )

    # Assert
    assert isinstance(response, Pronunciations)
    assert (
        response.audio
        == "https://test-bucket.s3.amazonaws.com/vocabs/en/hello/audio/pronunciation.mp3"
    )
    assert (
        response.syllables
        == "https://test-bucket.s3.amazonaws.com/vocabs/en/hello/audio/syllables.mp3"
    )


@pytest.mark.anyio
@patch("vocab_processor.tools.pronunciation_tool.is_lambda_context", return_value=True)
@patch("vocab_processor.tools.pronunciation_tool.boto3")
@patch("vocab_processor.tools.pronunciation_tool.generate_vocab_s3_paths")
@patch("vocab_processor.tools.pronunciation_tool.AsyncElevenLabs")
@patch("vocab_processor.tools.pronunciation_tool.upload_stream_to_s3")
@patch("os.getenv")
async def test_get_pronunciation_mixed_reuse_and_generate(
    mock_getenv,
    mock_upload_s3,
    mock_eleven_labs,
    mock_generate_s3_paths,
    mock_boto3,
    mock_is_lambda_context,
):
    # Arrange
    target_word = "hello"
    target_syllables = ["hel", "lo"]
    target_language = Language.ENGLISH

    # Mock environment and S3 paths
    mock_getenv.return_value = "test-bucket"
    mock_generate_s3_paths.return_value = {"audio_prefix": "vocabs/en/hello/audio"}

    # Mock S3 client to simulate only audio file exists (not syllables)
    mock_s3_client = MagicMock()
    mock_boto3.client.return_value = mock_s3_client

    def head_object_side_effect(Bucket, Key):
        if "pronunciation.mp3" in Key:
            return {}  # Audio file exists
        else:
            raise mock_s3_client.exceptions.NoSuchKey("Syllables not found")

    mock_s3_client.head_object.side_effect = head_object_side_effect
    mock_s3_client.exceptions.NoSuchKey = Exception

    # Mock ElevenLabs and upload for syllables generation
    mock_client = MagicMock()
    mock_eleven_labs.return_value = mock_client
    mock_upload_s3.return_value = (
        "https://test-bucket.s3.amazonaws.com/vocabs/en/hello/audio/syllables.mp3"
    )

    # Mock audio generation
    async def mock_audio_generator():
        yield b"mock_syllables_data"

    with patch(
        "vocab_processor.tools.pronunciation_tool.generate_audio_with_retry",
        return_value=mock_audio_generator(),
    ):
        # Act
        response = await get_pronunciation.ainvoke(
            {
                "target_word": target_word,
                "target_syllables": target_syllables,
                "target_language": target_language,
            }
        )

    # Assert
    assert isinstance(response, Pronunciations)
    # Should reuse existing audio file
    assert (
        response.audio
        == "https://test-bucket.s3.amazonaws.com/vocabs/en/hello/audio/pronunciation.mp3"
    )
    # Should generate new syllables file
    assert (
        response.syllables
        == "https://test-bucket.s3.amazonaws.com/vocabs/en/hello/audio/syllables.mp3"
    )

    # Should only upload syllables file (audio was reused)
    assert mock_upload_s3.call_count == 1


@pytest.mark.anyio
@patch("vocab_processor.tools.pronunciation_tool.is_lambda_context", return_value=True)
@patch("vocab_processor.tools.pronunciation_tool.boto3")
@patch("vocab_processor.tools.pronunciation_tool.generate_vocab_s3_paths")
@patch("os.getenv")
async def test_get_pronunciation_s3_error_fallback(
    mock_getenv, mock_generate_s3_paths, mock_boto3, mock_is_lambda_context
):
    # Arrange
    target_word = "hello"
    target_syllables = []  # Single syllable, no syllables file needed
    target_language = Language.ENGLISH

    # Mock environment and S3 paths
    mock_getenv.side_effect = lambda key: (
        "test-bucket" if key == "S3_MEDIA_BUCKET_NAME" else None
    )
    mock_generate_s3_paths.return_value = {"audio_prefix": "vocabs/en/hello/audio"}

    # Mock S3 client to throw error
    mock_s3_client = MagicMock()
    mock_boto3.client.return_value = mock_s3_client
    mock_s3_client.head_object.side_effect = Exception("S3 connection error")

    # Mock ElevenLabs and upload for fallback generation
    with patch("vocab_processor.tools.pronunciation_tool.AsyncElevenLabs"), patch(
        "vocab_processor.tools.pronunciation_tool.upload_stream_to_s3",
        return_value="https://test-bucket.s3.amazonaws.com/fallback-audio.mp3",
    ), patch(
        "vocab_processor.tools.pronunciation_tool.generate_audio_with_retry"
    ) as mock_generate:

        async def mock_audio_generator():
            yield b"fallback_audio_data"

        mock_generate.return_value = mock_audio_generator()

        # Act
        response = await get_pronunciation.ainvoke(
            {
                "target_word": target_word,
                "target_syllables": target_syllables,
                "target_language": target_language,
            }
        )

    # Assert
    assert isinstance(response, Pronunciations)
    # Should fallback to generation when S3 check fails
    assert response.audio == "https://test-bucket.s3.amazonaws.com/fallback-audio.mp3"
    assert response.syllables is None
