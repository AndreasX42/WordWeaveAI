from unittest.mock import AsyncMock, patch

import pytest

from vocab_processor.constants import Language, PartOfSpeech
from vocab_processor.tools.classification_tool import (
    ClassificationResponse,
    WordClassification,
    get_classification,
)


@pytest.mark.anyio
@patch(
    "vocab_processor.tools.classification_tool.create_llm_response",
    new_callable=AsyncMock,
)
@patch(
    "vocab_processor.tools.classification_tool.check_word_exists",
    new_callable=AsyncMock,
)
async def test_get_classification(mock_check_word_exists, mock_create_llm_response):
    # Arrange
    source_word = "test_word"
    source_language = Language.ENGLISH
    target_language = Language.SPANISH

    mock_llm_response = WordClassification(
        source_word="test_word",
        source_definition=["a word for testing"],
        source_part_of_speech=PartOfSpeech.NOUN,
        source_article="a",
        source_additional_info="common word",
        word_exists=None,
        existing_item=None,
    )
    mock_create_llm_response.return_value = mock_llm_response

    mock_check_word_exists.return_value = {
        "exists": False,
        "existing_item": None,
    }

    # Act
    result = await get_classification.ainvoke(
        {
            "source_word": source_word,
            "source_language": source_language,
            "target_language": target_language,
        }
    )

    # Assert
    assert isinstance(result, ClassificationResponse)
    assert result.result.source_word == "test_word"
    assert result.result.source_definition == ["a word for testing"]
    assert result.result.source_part_of_speech == PartOfSpeech.NOUN
    assert result.result.source_article == "a"
    assert result.result.source_additional_info == "common word"
    assert result.result.word_exists is False
    assert result.result.existing_item is None
    assert result.prompt != ""

    mock_create_llm_response.assert_called_once()
    mock_check_word_exists.assert_called_once_with(
        base_word="test_word",
        source_language="en",
        target_language="es",
        source_part_of_speech=PartOfSpeech.NOUN,
    )
