from aws_lambda_powertools import Logger
from vocab_processor.tools import *
from vocab_processor.utils.state import VocabState

logger = Logger(service="vocab-processor")


async def node_validate_source_word(state: VocabState) -> VocabState:
    """Validate the source word for spelling, ambiguity, and clarity."""

    validation_result = await validate_word.ainvoke(
        input={
            "word": state.source_word,
            "target_language": state.target_language,
        }
    )

    logger.debug(
        "validation_result",
        word=state.source_word,
        is_valid=validation_result.is_valid,
        source_language=(
            str(validation_result.source_language)
            if validation_result.source_language
            else None
        ),
    )

    if validation_result.is_valid:
        return {
            "validation_passed": True,
            "source_language": validation_result.source_language,
        }
    else:
        return {
            "validation_passed": False,
            "validation_message": validation_result.message,
            "suggested_words": validation_result.suggestions,
        }


async def node_get_classification(state: VocabState) -> VocabState:
    """Detect the language of the input word."""
    response = await get_classification.ainvoke(
        input={
            "source_word": state.source_word,
            "source_language": state.source_language,
        }
    )

    # print(f"Categorization: {response}")

    return {
        "source_definition": response.source_definition,
        "source_part_of_speech": response.source_part_of_speech,
        "source_article": response.source_article,
    }


async def node_get_translation(state: VocabState) -> VocabState:
    """Translate the word to the target language."""
    response = await get_translation.ainvoke(
        input={
            "source_word": state.source_word,
            "source_language": state.source_language,
            "target_language": state.target_language,
            "source_part_of_speech": state.source_part_of_speech,
        }
    )

    # print(f"Translation: {response}")

    return {
        "target_word": response.target_word,
        "target_part_of_speech": response.target_part_of_speech,
        "target_article": response.target_article,
    }


async def node_get_synonyms(state: VocabState) -> VocabState:
    """Fetch synonyms for the word."""
    response = await get_synonyms.ainvoke(
        input={
            "target_word": state.target_word,
            "target_language": state.target_language,
            "target_part_of_speech": state.target_part_of_speech,
        }
    )

    # print(f"Synonyms: {response}")

    return {"synonyms": response.synonyms}


async def node_get_syllables(state: VocabState) -> VocabState:
    """Generate syllable breakdown for the target word."""
    response = await get_syllables.ainvoke(
        input={
            "target_word": state.target_word,
            "target_language": state.target_language,
        }
    )

    # print(f"Syllables: {response.syllables}")

    return {"target_syllables": response.syllables}


async def node_get_pronunciation(state: VocabState) -> VocabState:
    """Generate pronunciation audio for word and syllables."""

    result = await get_pronunciation.ainvoke(
        input={
            "target_word": state.target_word,
            "target_syllables": state.target_syllables,
            "target_language": state.target_language,
        }
    )

    # print(f"Pronunciation result: {result}")

    return {"pronunciations": result}


async def node_get_media(state: VocabState) -> VocabState:
    """Get visual media for the word."""
    response = await get_media.ainvoke(
        input={
            "source_word": state.source_word,
            "target_word": state.target_word,
            "source_language": state.source_language,
            "target_language": state.target_language,
        }
    )

    # print(f"Memory aid: {response}")

    return {
        "media": response.get("media", None),
        "english_word": response.get("english_word", None),
        "search_query": response.get("search_query", []),
        "media_reused": response.get("media_reused", False),
    }


async def node_get_examples(state: VocabState) -> VocabState:
    """Generate example sentences."""
    response = await get_examples.ainvoke(
        input={
            "source_word": state.source_word,
            "target_word": state.target_word,
            "source_language": state.source_language,
            "target_language": state.target_language,
        }
    )

    # print(f"Examples: {response}")

    return {"examples": response.examples}


async def node_get_conjugation(state: VocabState) -> VocabState:
    """Get verb conjugation if applicable."""
    if state.target_part_of_speech != "verb":
        return {"conjugation": None}

    response = await get_conjugation.ainvoke(
        input={
            "target_word": state.target_word,
            "target_language": state.target_language,
            "target_part_of_speech": state.target_part_of_speech,
        }
    )

    # print(f"Conjugation: {response}")

    return {"conjugation": response}
