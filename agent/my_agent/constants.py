from enum import Enum

class Language(str, Enum):
    """Supported languages with their metadata."""
    ENGLISH = "English"
    SPANISH = "Spanish"
    GERMAN = "German"

    @property
    def code(self) -> str:
        """ISO 639-1 language code."""
        codes = {
            Language.ENGLISH: "en",
            Language.SPANISH: "es",
            Language.GERMAN: "de"
        }
        return codes[self]

    @property
    def native_name(self) -> str:
        """Name of the language in its native form."""
        names = {
            Language.ENGLISH: "English",
            Language.SPANISH: "Español",
            Language.GERMAN: "Deutsch"
        }
        return names[self]

    @classmethod
    def from_code(cls, code: str) -> "Language":
        """Get Language enum from ISO code."""
        code_map = {
            "en": cls.ENGLISH,
            "es": cls.SPANISH,
            "de": cls.GERMAN
        }
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
            self.INTERJECTION: "interjection"
        }
        return categories[self]

    @property
    def has_gender(self) -> bool:
        """Whether this part of speech has grammatical gender."""
        return self in [self.FEMININE_NOUN, self.MASCULINE_NOUN, self.ADJECTIVE, self.ARTICLE]

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


from langchain_openai import ChatOpenAI
from instructor import from_openai, Mode
from openai import AsyncOpenAI
import os
from dotenv import load_dotenv

load_dotenv()

client = AsyncOpenAI(api_key=os.getenv("OPENAI_API_KEY"))
instructor_llm = from_openai(client=client, model="gpt-4.1-mini-2025-04-14", temperature=0.2, mode=Mode.JSON)

chat_model = ChatOpenAI(
    model="gpt-3.5-turbo",
    temperature=0,
    openai_api_key=os.getenv("OPENAI_API_KEY")
)

instructor_llm = instructor_llm
agent_llm: ChatOpenAI = chat_model