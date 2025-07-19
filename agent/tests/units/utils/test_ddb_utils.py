from unittest.mock import MagicMock, patch

import pytest

from vocab_processor.constants import Language, PartOfSpeech
from vocab_processor.utils.ddb_utils import (
    check_word_exists,
    get_existing_media_for_search_words,
)


@pytest.mark.anyio
@patch("vocab_processor.utils.ddb_utils.is_lambda_context", return_value=True)
@patch("vocab_processor.utils.ddb_utils.get_vocab_table")
async def test_check_word_exists_found(mock_get_vocab_table, mock_is_lambda_context):
    # Arrange
    base_word = "test"
    source_language = Language.ENGLISH
    target_language = "es"
    source_part_of_speech = PartOfSpeech.NOUN

    mock_response = {"Items": [{"PK": "test_pk", "SK": "test_sk", "data": "test_data"}]}

    # Mock asyncio.to_thread to return the mock response
    with patch("asyncio.to_thread") as mock_to_thread:
        mock_to_thread.return_value = mock_response

        # Act
        result = await check_word_exists(
            base_word, source_language, target_language, source_part_of_speech
        )

        # Assert
        assert result["exists"] is True
        assert result["existing_item"] == {
            "PK": "test_pk",
            "SK": "test_sk",
            "data": "test_data",
        }
        mock_to_thread.assert_called_once()


@pytest.mark.anyio
@patch("vocab_processor.utils.ddb_utils.is_lambda_context", return_value=True)
@patch("vocab_processor.utils.ddb_utils.get_vocab_table")
async def test_check_word_exists_not_found(
    mock_get_vocab_table, mock_is_lambda_context
):
    # Arrange
    base_word = "nonexistent"
    source_language = Language.ENGLISH
    target_language = "es"
    source_part_of_speech = PartOfSpeech.NOUN

    mock_response = {"Items": []}

    # Mock asyncio.to_thread to return the mock response
    with patch("asyncio.to_thread") as mock_to_thread:
        mock_to_thread.return_value = mock_response

        # Act
        result = await check_word_exists(
            base_word, source_language, target_language, source_part_of_speech
        )

        # Assert
        assert result["exists"] is False
        assert result["existing_item"] is None
        assert mock_to_thread.call_count == 2  # Query + put_item for placeholder


@pytest.mark.anyio
@patch("vocab_processor.utils.ddb_utils.is_lambda_context", return_value=True)
@patch("vocab_processor.utils.ddb_utils.get_media_table")
async def test_get_existing_media_found(mock_get_media_table, mock_is_lambda_context):
    # Arrange
    search_words = ["test", "photo"]
    mock_media_table = MagicMock()
    mock_get_media_table.return_value = mock_media_table

    # Simulate the actual sequence of calls the function makes
    async def mock_get_item_side_effect(Key, **kwargs):
        if Key.get("PK") == "SEARCH#test":
            return {
                "Item": {
                    "media_ref": "media_ref_1",
                    "search_term": "test",
                    "usage_count": 5,
                    "last_used": "2023-01-01T00:00:00+00:00",
                }
            }
        elif Key.get("PK") == "SEARCH#photo":
            return {
                "Item": {
                    "media_ref": "media_ref_2",
                    "search_term": "photo",
                    "usage_count": 3,
                    "last_used": "2023-01-01T00:00:00+00:00",
                }
            }
        elif Key.get("PK") == "media_ref_1":
            return {"Item": {"media": {"url": "test_url", "alt": "test image"}}}
        return {}

    async def mock_update_item_side_effect(**kwargs):
        return None

    # Use side_effect to handle different calls
    with patch("asyncio.to_thread") as mock_to_thread:
        mock_to_thread.side_effect = [
            {
                "Item": {
                    "media_ref": "media_ref_1",
                    "search_term": "test",
                    "usage_count": 5,
                    "last_used": "2023-01-01T00:00:00+00:00",
                }
            },  # First search
            {
                "Item": {
                    "media_ref": "media_ref_2",
                    "search_term": "photo",
                    "usage_count": 3,
                    "last_used": "2023-01-01T00:00:00+00:00",
                }
            },  # Second search
            {
                "Item": {"media": {"url": "test_url", "alt": "test image"}}
            },  # Media lookup
            None,  # Usage update
        ]

        # Act
        result = await get_existing_media_for_search_words(search_words)

        # Assert
        assert result is not None
        assert result["url"] == "test_url"
        assert result["matched_word"] == "test"
        assert result["media_ref"] == "media_ref_1"
        # Should be called multiple times
        assert mock_to_thread.call_count >= 3


@pytest.mark.anyio
@patch("vocab_processor.utils.ddb_utils.is_lambda_context", return_value=True)
@patch("vocab_processor.utils.ddb_utils.get_media_table")
@patch("asyncio.to_thread")
async def test_get_existing_media_not_found(
    mock_to_thread, mock_get_media_table, mock_is_lambda_context
):
    # Arrange
    search_words = ["nonexistent"]
    mock_media_table = MagicMock()
    mock_get_media_table.return_value = mock_media_table

    # Mock empty responses
    mock_to_thread.return_value = {}

    # Act
    result = await get_existing_media_for_search_words(search_words)

    # Assert
    assert result is None
    mock_to_thread.assert_called()
