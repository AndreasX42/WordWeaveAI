from unittest.mock import AsyncMock, patch

import pytest

from vocab_processor.constants import Language, PartOfSpeech
from vocab_processor.tools.syllables_tool import (
    SyllableBreakdown,
    SyllablesResponse,
    get_syllables,
)
from vocab_processor.tools.synonyms_tool import Synonyms, SynonymsResponse, get_synonyms
from vocab_processor.tools.translation_tool import (
    Translation,
    TranslationResponse,
    get_translation,
)


@pytest.mark.anyio
@patch(
    "vocab_processor.tools.syllables_tool.create_llm_response", new_callable=AsyncMock
)
async def test_get_syllables(mock_create_llm_response):
    # Arrange
    target_word = "ciudad"
    target_language = Language.SPANISH
    mock_response = SyllableBreakdown(
        syllables=["ciu", "dad"], phonetic_guide="[θju.'ðað]"
    )
    mock_create_llm_response.return_value = mock_response

    # Act
    response = await get_syllables.ainvoke(
        {"target_word": target_word, "target_language": target_language}
    )

    # Assert
    assert isinstance(response, SyllablesResponse)
    assert response.result == mock_response
    mock_create_llm_response.assert_called_once()


@pytest.mark.anyio
@patch(
    "vocab_processor.tools.synonyms_tool.create_llm_response", new_callable=AsyncMock
)
async def test_get_synonyms(mock_create_llm_response):
    # Arrange
    target_word = "happy"
    source_language = Language.ENGLISH
    target_language = Language.ENGLISH
    target_part_of_speech = PartOfSpeech.ADJECTIVE
    mock_response = Synonyms(synonyms=[])
    mock_create_llm_response.return_value = mock_response

    # Act
    response = await get_synonyms.ainvoke(
        {
            "target_word": target_word,
            "source_language": source_language,
            "target_language": target_language,
            "target_part_of_speech": target_part_of_speech,
        }
    )

    # Assert
    assert isinstance(response, SynonymsResponse)
    assert response.result == mock_response
    mock_create_llm_response.assert_called_once()


@pytest.mark.anyio
@patch(
    "vocab_processor.tools.translation_tool.create_llm_response", new_callable=AsyncMock
)
async def test_get_translation(mock_create_llm_response):
    # Arrange
    source_word = "hello"
    source_language = Language.ENGLISH
    target_language = Language.SPANISH
    source_part_of_speech = PartOfSpeech.INTERJECTION
    mock_response = Translation(
        target_word="hola",
        target_part_of_speech=PartOfSpeech.INTERJECTION,
        english_word="hello",
    )
    mock_create_llm_response.return_value = mock_response

    # Act
    response = await get_translation.ainvoke(
        {
            "source_word": source_word,
            "source_language": source_language,
            "target_language": target_language,
            "source_part_of_speech": source_part_of_speech,
        }
    )

    # Assert
    assert isinstance(response, TranslationResponse)
    assert response.result == mock_response
    mock_create_llm_response.assert_called_once()
