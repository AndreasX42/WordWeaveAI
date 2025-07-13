from typing import List, Optional, TypedDict


class TestCaseDict(TypedDict, total=False):
    source_word: str
    target_language: str
    source_language: Optional[str]
    description: Optional[str]
    tags: Optional[List[str]]


TEST_CASES: List[TestCaseDict] = [
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
]
