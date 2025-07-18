from unittest.mock import AsyncMock, patch

import pytest

from vocab_processor.constants import Language, PartOfSpeech
from vocab_processor.schemas.english_conj_model import EnglishVerbConjugation
from vocab_processor.tools.conjugation_tool import ConjugationResponse, get_conjugation


@pytest.mark.anyio
async def test_get_conjugation_not_conjugatable():
    # Arrange
    target_word = "house"
    target_language = Language.ENGLISH
    target_part_of_speech = PartOfSpeech.NOUN

    # Act
    response = await get_conjugation.ainvoke(
        {
            "target_word": target_word,
            "target_language": target_language,
            "target_part_of_speech": target_part_of_speech,
        }
    )

    # Assert
    assert "not a verb" in response.result.conjugation


@pytest.mark.anyio
@patch(
    "vocab_processor.tools.conjugation_tool.create_llm_response", new_callable=AsyncMock
)
async def test_get_conjugation_with_exception(mock_create_llm_response):
    # Arrange
    target_word = "run"
    target_language = Language.ENGLISH
    target_part_of_speech = PartOfSpeech.VERB

    # Mock the LLM response to raise an exception
    mock_create_llm_response.side_effect = Exception("LLM Error")

    # Act
    response = await get_conjugation.ainvoke(
        {
            "target_word": target_word,
            "target_language": target_language,
            "target_part_of_speech": target_part_of_speech,
        }
    )

    # Assert
    assert isinstance(response, ConjugationResponse)
    assert "Error creating conjugation" in response.result.conjugation
    assert response.prompt == ""


@pytest.mark.anyio
@patch(
    "vocab_processor.tools.conjugation_tool.create_llm_response", new_callable=AsyncMock
)
async def test_get_conjugation_success(mock_create_llm_response):
    # Arrange
    target_word = "run"
    target_language = Language.ENGLISH
    target_part_of_speech = PartOfSpeech.VERB

    # Mock the LLM response
    mock_conjugation = EnglishVerbConjugation(
        non_personal_forms={
            "infinitive": "to run",
            "present_participle": "running",
            "past_participle": "run",
        },
        indicative={
            "present": {
                "I": "run",
                "you": "run",
                "he/she/it": "runs",
                "we": "run",
                "you_plural": "run",
                "they": "run",
            },
            "past": {
                "I": "ran",
                "you": "ran",
                "he/she/it": "ran",
                "we": "ran",
                "you_plural": "ran",
                "they": "ran",
            },
        },
        subjunctive={
            "present": {
                "I": "run",
                "you": "run",
                "he/she/it": "run",
                "we": "run",
                "you_plural": "run",
                "they": "run",
            },
            "past": {
                "I": "ran",
                "you": "ran",
                "he/she/it": "ran",
                "we": "ran",
                "you_plural": "ran",
                "they": "ran",
            },
        },
    )
    mock_create_llm_response.return_value = mock_conjugation

    # Act
    response = await get_conjugation.ainvoke(
        {
            "target_word": target_word,
            "target_language": target_language,
            "target_part_of_speech": target_part_of_speech,
        }
    )

    # Assert
    assert isinstance(response, ConjugationResponse)
    assert response.result.conjugation == mock_conjugation
    assert response.prompt != ""
    mock_create_llm_response.assert_called_once()
