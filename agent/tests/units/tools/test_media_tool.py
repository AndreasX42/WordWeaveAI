from unittest.mock import AsyncMock, patch

import pytest

from vocab_processor.constants import Language
from vocab_processor.tools.media_tool import get_media


@pytest.mark.anyio
@patch("vocab_processor.tools.media_tool.get_existing_media_for_search_words")
@patch("vocab_processor.tools.media_tool.create_llm_response", new_callable=AsyncMock)
async def test_get_media_existing_media(
    mock_create_llm_response, mock_get_existing_media
):
    # Arrange
    source_word = "casa"
    target_word = "house"
    english_word = "house"
    source_language = Language.SPANISH
    target_language = Language.ENGLISH

    # Mock existing media with the structure expected by the function
    mock_get_existing_media.return_value = {
        "url": "https://example.com/house.jpg",
        "matched_word": "house",
        "media_ref": "media_ref_1",
        "alt": "A beautiful house",
        "src": {
            "large2x": "https://example.com/house_large2x.jpg",
            "large": "https://example.com/house_large.jpg",
            "medium": "https://example.com/house_medium.jpg",
        },
    }

    # Mock SearchQueryResult
    from vocab_processor.schemas.media_model import SearchQueryResult

    mock_search_query = SearchQueryResult(search_query=["house", "home"])
    mock_create_llm_response.return_value = mock_search_query

    # Act
    response = await get_media.ainvoke(
        {
            "source_word": source_word,
            "target_word": target_word,
            "english_word": english_word,
            "source_language": source_language,
            "target_language": target_language,
        }
    )

    # Assert
    assert isinstance(response, dict)
    assert "media" in response
    assert "media_reused" in response
    assert response["media_reused"] is True
    assert "search_query" in response
    # Should call LLM twice: once for search query, once for media adaptation
    assert mock_create_llm_response.call_count == 2
    mock_get_existing_media.assert_called_once()


@pytest.mark.anyio
@patch("vocab_processor.tools.media_tool.get_existing_media_for_search_words")
@patch("vocab_processor.tools.media_tool.create_llm_response", new_callable=AsyncMock)
@patch("vocab_processor.tools.media_tool.is_lambda_context", return_value=False)
async def test_get_media_new_media(
    mock_is_lambda_context, mock_create_llm_response, mock_get_existing_media
):
    # Arrange
    source_word = "casa"
    target_word = "house"
    english_word = "house"
    source_language = Language.SPANISH
    target_language = Language.ENGLISH

    # Mock no existing media
    mock_get_existing_media.return_value = None

    # Mock search query result
    from vocab_processor.schemas.media_model import SearchQueryResult

    mock_search_query = SearchQueryResult(search_query=["house", "home"])
    mock_create_llm_response.return_value = mock_search_query

    # Act
    response = await get_media.ainvoke(
        {
            "source_word": source_word,
            "target_word": target_word,
            "english_word": english_word,
            "source_language": source_language,
            "target_language": target_language,
        }
    )

    # Assert
    assert isinstance(response, dict)
    # In dev mode, should return mock data
    assert "ERROR" not in str(response)
    mock_create_llm_response.assert_called_once()
    mock_get_existing_media.assert_called_once()
