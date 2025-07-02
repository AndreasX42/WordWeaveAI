import os
from enum import Enum

import boto3
from instructor import Mode, from_bedrock, from_openai
from openai import AsyncOpenAI


class Language(str, Enum):
    """Supported languages with their metadata."""

    ENGLISH = "English"
    SPANISH = "Spanish"
    GERMAN = "German"

    @property
    def code(self) -> str:
        """ISO 639-1 language code."""
        codes = {Language.ENGLISH: "en", Language.SPANISH: "es", Language.GERMAN: "de"}
        return codes[self]

    @property
    def native_name(self) -> str:
        """Name of the language in its native form."""
        names = {
            Language.ENGLISH: "English",
            Language.SPANISH: "Español",
            Language.GERMAN: "Deutsch",
        }
        return names[self]

    @classmethod
    def from_code(cls, code: str) -> "Language":
        """Get Language enum from ISO code."""
        code_map = {"en": cls.ENGLISH, "es": cls.SPANISH, "de": cls.GERMAN}
        return code_map[code.lower()]

    @classmethod
    def all_values(cls) -> list[str]:
        """Get all language string values."""
        return [lang.value for lang in cls]


class PartOfSpeech(str, Enum):
    """Parts of speech with metadata for language learning."""

    FEMININE_NOUN = "feminine noun"
    MASCULINE_NOUN = "masculine noun"
    VERB = "verb"
    ADJECTIVE = "adjective"
    ADVERB = "adverb"
    PREPOSITION = "preposition"
    CONJUNCTION = "conjunction"
    PRONOUN = "pronoun"
    ARTICLE = "article"
    INTERJECTION = "interjection"

    @property
    def category(self) -> str:
        """Get the general grammatical category."""
        categories = {
            self.FEMININE_NOUN: "noun",
            self.MASCULINE_NOUN: "noun",
            self.VERB: "verb",
            self.ADJECTIVE: "adjective",
            self.ADVERB: "adverb",
            self.PREPOSITION: "preposition",
            self.CONJUNCTION: "conjunction",
            self.PRONOUN: "pronoun",
            self.ARTICLE: "article",
            self.INTERJECTION: "interjection",
        }
        return categories[self]

    @property
    def has_gender(self) -> bool:
        """Whether this part of speech has grammatical gender."""
        return self in [
            self.FEMININE_NOUN,
            self.MASCULINE_NOUN,
            self.ADJECTIVE,
            self.ARTICLE,
        ]

    @property
    def is_conjugatable(self) -> bool:
        """Whether this part of speech can be conjugated/inflected."""
        return self == self.VERB

    @property
    def is_declinable(self) -> bool:
        """Whether this part of speech can be declined (nouns, adjectives)."""
        return self.category in ["noun", "adjective", "pronoun", "article"]

    @classmethod
    def get_by_category(cls, category: str) -> list["PartOfSpeech"]:
        """Get all parts of speech in a category."""
        return [pos for pos in cls if pos.category == category]

    @classmethod
    def all_values(cls) -> list[str]:
        """Get all part of speech string values."""
        return [pos.value for pos in cls]


client = AsyncOpenAI(api_key=os.getenv("OPENAI_API_KEY"))

# Cache instructor client to avoid recreation
_instructor_oai_gpt4_1_mini = None
_instructor_oai_gpt4_1 = None
_instructor_aws_claude4 = None


def get_instructor_oai_gpt4_1_mini():
    """Get cached instructor client for gpt-4.1-mini."""
    global _instructor_oai_gpt4_1_mini
    if _instructor_oai_gpt4_1_mini is None:
        _instructor_oai_gpt4_1_mini = from_openai(
            client=client,
            model="gpt-4.1-mini-2025-04-14",
            temperature=0.2,
            mode=Mode.JSON,
        )
    return _instructor_oai_gpt4_1_mini


def get_instructor_oai_gpt4_1():
    """Get cached instructor client for gpt-4.1 for validation tasks requiring highest accuracy."""
    global _instructor_oai_gpt4_1
    if _instructor_oai_gpt4_1 is None:
        _instructor_oai_gpt4_1 = from_openai(
            client=client,
            model="gpt-4.1-2025-04-14",
            temperature=0.2,
            mode=Mode.JSON,
        )
    return _instructor_oai_gpt4_1


def get_instructor_aws_claude4():
    """Get cached Instructor client for Claude-4 via AWS Bedrock."""
    global _instructor_aws_claude4
    if _instructor_aws_claude4 is None:
        try:
            bedrock_client = boto3.client(
                "bedrock-runtime", region_name=os.getenv("AWS_REGION", "us-east-1")
            )
        except Exception as e:
            raise RuntimeError(
                f"Failed to create Bedrock client. Ensure AWS credentials are configured: {e}"
            ) from e

        sync_instructor_client = from_bedrock(
            client=bedrock_client,
            mode=Mode.BEDROCK_JSON,
            temperature=0.2,
            model="us.anthropic.claude-sonnet-4-20250514-v1:0",
        )

        # Wrap it in a proper async interface
        import asyncio

        from instructor import AsyncInstructor

        async def async_create(*args, **kwargs):
            """Async wrapper that properly handles blocking calls."""
            return await asyncio.to_thread(
                sync_instructor_client.create, *args, **kwargs
            )

        # Create a simple async wrapper class
        class AsyncBedrockInstructor:
            def __init__(self, sync_client):
                self.sync_client = sync_client

            async def create(self, *args, **kwargs):
                """Async wrapper that properly handles blocking calls."""
                return await asyncio.to_thread(self.sync_client.create, *args, **kwargs)

        _instructor_aws_claude4 = AsyncBedrockInstructor(sync_instructor_client)

    return _instructor_aws_claude4


instructor_oai_gpt4_1_mini = get_instructor_oai_gpt4_1_mini()
instructor_oai_gpt4_1 = get_instructor_oai_gpt4_1()
instructor_aws_claude4 = get_instructor_aws_claude4()


class LLMVariant(str, Enum):
    """Supported LLM back-ends."""

    GPT41M = "gpt41m"  # OpenAI GPT-4.1-mini
    GPT41 = "gpt41"  # OpenAI GPT-4.1
    CLAUDE4S = "claude4s"  # Claude-4 Sonnet via AWS Bedrock


# Map each variant to its cached Instructor client
LLM_PROVIDERS = {
    LLMVariant.GPT41M: instructor_oai_gpt4_1_mini,
    LLMVariant.GPT41: instructor_oai_gpt4_1,
    LLMVariant.CLAUDE4S: instructor_aws_claude4,
}


def get_llm_client(provider: LLMVariant = LLMVariant.GPT41M):
    """Return the Instructor client for the requested provider key.

    Args:
        provider: LLMVariant enum member specifying which LLM to use
    """
    return LLM_PROVIDERS[provider]
