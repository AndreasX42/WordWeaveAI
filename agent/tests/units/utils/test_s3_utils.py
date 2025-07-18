from unittest.mock import patch

import pytest

from vocab_processor.constants import Language
from vocab_processor.utils.s3_utils import (
    generate_english_image_s3_paths,
    generate_vocab_s3_paths,
    upload_bytes_to_s3,
    upload_stream_to_s3,
)


def test_generate_vocab_s3_paths():
    # Arrange
    target_language = Language.SPANISH
    target_word = "palabra"

    # Act
    paths = generate_vocab_s3_paths(target_language, target_word)

    # Assert
    assert paths["base_prefix"] == "vocabs/es/palabra"
    assert paths["audio_prefix"] == "vocabs/es/palabra/audio"
    assert paths["image_prefix"] == "vocabs/es/palabra/images"


def test_generate_english_image_s3_paths():
    # Arrange
    english_word = "word"

    # Act
    paths = generate_english_image_s3_paths(english_word)

    # Assert
    assert paths["image_prefix"] == "vocabs/en/word/images"
    assert paths["large2x_key"] == "vocabs/en/word/images/large2x.jpg"
    assert paths["large_key"] == "vocabs/en/word/images/large.jpg"
    assert paths["medium_key"] == "vocabs/en/word/images/medium.jpg"


@pytest.mark.anyio
@patch("vocab_processor.utils.s3_utils.is_lambda_context", return_value=True)
@patch("vocab_processor.utils.s3_utils.S3_BUCKET", "test-bucket")
@patch("asyncio.to_thread")
async def test_upload_bytes_to_s3(mock_to_thread, mock_is_lambda_context):
    # Arrange
    data = b"test data"
    s3_key = "test/key"
    content_type = "text/plain"

    # Mock the asyncio.to_thread call
    mock_to_thread.return_value = (
        None  # S3 put_object doesn't return anything meaningful
    )

    # Act
    url = await upload_bytes_to_s3(data, s3_key, content_type)

    # Assert
    assert url == "https://test-bucket.s3.amazonaws.com/test/key"
    mock_to_thread.assert_called_once()
    # Verify the call was made with correct parameters
    call_args = mock_to_thread.call_args
    assert call_args[1]["Bucket"] == "test-bucket"  # type: ignore
    assert call_args[1]["Key"] == s3_key  # type: ignore
    assert call_args[1]["Body"] == data  # type: ignore
    assert call_args[1]["ContentType"] == content_type  # type: ignore


@pytest.mark.anyio
@patch("vocab_processor.utils.s3_utils.is_lambda_context", return_value=False)
async def test_upload_bytes_to_s3_local_mode(mock_is_lambda_context):
    # Arrange
    data = b"test data"
    s3_key = "test/key"
    content_type = "text/plain"

    # Act
    url = await upload_bytes_to_s3(data, s3_key, content_type)

    # Assert
    assert url == "https://mock-s3-bucket.local/test/key"


@pytest.mark.anyio
@patch("vocab_processor.utils.s3_utils.is_lambda_context", return_value=False)
async def test_upload_stream_to_s3_local_mode(mock_is_lambda_context):
    # Arrange
    async def stream():
        yield b"chunk1"
        yield b"chunk2"

    s3_key = "test/key"
    content_type = "text/plain"

    # Act
    url = await upload_stream_to_s3(stream(), s3_key, content_type)

    # Assert
    assert url == "https://mock-s3-bucket.local/test/key"


@pytest.mark.anyio
@patch("vocab_processor.utils.s3_utils.is_lambda_context", return_value=True)
@patch("vocab_processor.utils.s3_utils.upload_bytes_to_s3")
async def test_upload_stream_to_s3_lambda_mode(
    mock_upload_bytes, mock_is_lambda_context
):
    # Arrange
    async def stream():
        yield b"chunk1"
        yield b"chunk2"

    s3_key = "test/key"
    content_type = "text/plain"
    mock_upload_bytes.return_value = "https://test-bucket.s3.amazonaws.com/test/key"

    # Act
    url = await upload_stream_to_s3(stream(), s3_key, content_type)

    # Assert
    assert url == "https://test-bucket.s3.amazonaws.com/test/key"
    mock_upload_bytes.assert_called_once_with(b"chunk1chunk2", s3_key, content_type)
