from vocab_processor.tools.categrization_tool import get_classification
from vocab_processor.tools.translation_tool import get_translation
from vocab_processor.tools.pronounciation_tool import get_pronunciation
from vocab_processor.tools.synonyms_tool import get_synonyms
from vocab_processor.tools.media_tool import get_media
from vocab_processor.tools.examples_tool import get_examples
from vocab_processor.tools.conjugation_tool import get_conjugation
from vocab_processor.tools.validation_tool import validate_word
from vocab_processor.tools.syllables_tool import get_syllables

__all__ = [
    "get_classification",
    "get_translation",
    "get_pronunciation",
    "get_syllables",
    "get_synonyms",
    "get_media",
    "get_examples",
    "get_conjugation",
    "validate_word"
]