from typing import Optional, TypedDict


class TestCaseDict(TypedDict, total=False):
    source_word: str
    target_language: str
    source_language: Optional[str]
    description: Optional[str]
    tags: Optional[list[str]]


TEST_CASES: list[TestCaseDict] = [
    {
        "source_word": "to be",
        "target_language": "Spanish",
        "description": "English verb phrase to Spanish",
        "tags": ["verb-phrase", "basic"],
    },
    {
        "source_word": "serendipity",
        "source_language": "English",
        "target_language": "German",
        "description": "Complex English word to German",
        "tags": ["complex", "noun"],
    },
    {
        "source_word": "the cringe",
        "source_language": "English",
        "target_language": "German",
        "description": "English slang to German",
        "tags": ["slang", "modern"],
    },
    {
        "source_word": "Schadenfreude",
        "source_language": "German",
        "target_language": "English",
        "description": "German compound word to English",
        "tags": ["compound", "german"],
    },
    {
        "source_word": "Heimweh",
        "source_language": "German",
        "target_language": "Spanish",
        "description": "German compound word to Spanish",
        "tags": ["compound", "german"],
    },
    {
        "source_word": "fanfarronear",
        "target_language": "English",
        "description": "Spanish verb '-ear' to English",
        "tags": ["verb", "spanish"],
    },
    {
        "source_word": "über",
        "source_language": "German",
        "target_language": "English",
        "description": "German word with umlaut",
        "tags": ["umlaut", "german"],
    },
    {
        "source_word": "beautiful",
        "source_language": "English",
        "target_language": "Spanish",
        "description": "English adjective to Spanish",
        "tags": ["adjective", "basic"],
    },
    {
        "source_word": "quickly",
        "source_language": "English",
        "target_language": "German",
        "description": "English adverb to German",
        "tags": ["adverb", "basic"],
    },
    {
        "source_word": "mit",
        "source_language": "German",
        "target_language": "English",
        "description": "German preposition to English",
        "tags": ["preposition", "german"],
    },
    {
        "source_word": "aber",
        "source_language": "German",
        "target_language": "Spanish",
        "description": "German conjunction to Spanish",
        "tags": ["conjunction", "german"],
    },
    {
        "source_word": "yo",
        "source_language": "Spanish",
        "target_language": "English",
        "description": "Spanish pronoun to English",
        "tags": ["pronoun", "spanish"],
    },
    {
        "source_word": "el",
        "source_language": "Spanish",
        "target_language": "German",
        "description": "Spanish article to German",
        "tags": ["article", "spanish"],
    },
    {
        "source_word": "alfombra",
        "source_language": "Spanish",
        "target_language": "German",
        "description": "German noun to Spanish",
        "tags": ["noun", "german"],
    },
]
