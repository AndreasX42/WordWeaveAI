from unittest.mock import AsyncMock, patch

import pytest

from vocab_processor.constants import Language, PartOfSpeech
from vocab_processor.tools.examples_tool import (
    Examples,
    ExampleSentence,
    ExamplesResponse,
    get_examples,
)


@pytest.mark.anyio
@patch(
    "vocab_processor.tools.examples_tool.create_llm_response", new_callable=AsyncMock
)
async def test_get_examples(mock_create_llm_response):
    # Arrange
    source_word = "hello"
    target_word = "hola"
    source_language = Language.ENGLISH
    target_language = Language.SPANISH
    source_part_of_speech = PartOfSpeech.INTERJECTION
    target_part_of_speech = PartOfSpeech.INTERJECTION

    mock_examples = Examples(
        examples=[
            ExampleSentence(
                original="Hello, how are you doing today? I hope you are well.",
                translation="Hola, ¿cómo estás hoy? Espero que estés bien.",
                context="Common greeting and inquiry about well-being",
            ),
            ExampleSentence(
                original="Hello there! It's nice to meet you today.",
                translation="¡Hola! Es un placer conocerte hoy.",
                context="Friendly greeting when meeting someone new",
            ),
            ExampleSentence(
                original="I always say hello to my neighbors in the morning.",
                translation="Siempre saludo a mis vecinos por la mañana.",
                context="Habitual greeting behavior description",
            ),
        ]
    )
    mock_create_llm_response.return_value = mock_examples

    # Act
    response = await get_examples.ainvoke(
        {
            "source_word": source_word,
            "target_word": target_word,
            "source_language": source_language,
            "target_language": target_language,
            "source_part_of_speech": source_part_of_speech,
            "target_part_of_speech": target_part_of_speech,
        }
    )

    # Assert
    assert isinstance(response, ExamplesResponse)
    assert response.result == mock_examples
    assert len(response.result.examples) == 3
    assert (
        response.result.examples[0].original
        == "Hello, how are you doing today? I hope you are well."
    )
    assert (
        response.result.examples[0].translation
        == "Hola, ¿cómo estás hoy? Espero que estés bien."
    )
    mock_create_llm_response.assert_called_once()
