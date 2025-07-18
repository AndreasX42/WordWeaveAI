from unittest.mock import patch

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
@patch("vocab_processor.tools.pronunciation_tool.is_lambda_context", return_value=True)
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

    # Act - Since the tool will fail in lambda context without proper ElevenLabs setup,
    # we expect it to return an error response
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
