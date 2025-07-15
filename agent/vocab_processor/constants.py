import os
from enum import Enum

import boto3
from instructor import Mode, from_bedrock, from_openai
from openai import AsyncOpenAI


def is_tracing_enabled() -> bool:
    """Check if LangSmith tracing is enabled.

    Returns:
        bool: True if tracing is enabled, False otherwise
    """
    return os.getenv("LANGSMITH_TRACING_ENABLED", "false") == "true" and os.getenv(
        "LANGSMITH_API_KEY"
    )


if is_tracing_enabled():
    from langsmith import traceable
else:

    # Create a no-op traceable decorator for production
    def traceable(**kwargs):
        def decorator(func):
            return func

        return decorator


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
    NEUTER_NOUN = "neuter noun"
    NOUN = "noun"
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

# Cache instructor clients to avoid recreation and improve performance
_instructor_aws_claude4 = None
_instructor_node_executor_llm = None
_instructor_supervisor_llm = None


class TracedInstructorClient:
    """Wrapper for instructor clients with optional LangSmith tracing and token usage reporting.

    Tracing is controlled by environment variables:
    - LANGSMITH_TRACING_ENABLED: Set to "false", "0", or "no" to disable tracing
    - LANGSMITH_API_KEY: Must be set for tracing to work

    In production, set LANGSMITH_TRACING_ENABLED=false to disable tracing entirely.
    """

    def __init__(self, instructor_client, model_name: str):
        self.instructor_client = instructor_client
        self.model_name = model_name

    def _report_usage_to_langsmith(self, run_tree, completion, result, messages):
        """Report token usage and model info to LangSmith (only when tracing is enabled)."""
        if not is_tracing_enabled() or not run_tree:
            return

        # Set model metadata
        run_tree.extra = {**(run_tree.extra or {})}
        run_tree.extra["ls_model_name"] = self.model_name
        run_tree.extra["ls_provider"] = (
            "openai" if "gpt" in self.model_name.lower() else "anthropic"
        )

        # Extract token usage based on completion type
        if hasattr(completion, "usage") and completion.usage:
            # OpenAI format
            usage = {
                "prompt_tokens": completion.usage.prompt_tokens,
                "completion_tokens": completion.usage.completion_tokens,
                "total_tokens": completion.usage.total_tokens,
            }
        elif hasattr(completion, "meta") and completion.meta:
            # AWS Bedrock format
            input_tokens = getattr(completion.meta, "input_tokens", 0)
            output_tokens = getattr(completion.meta, "output_tokens", 0)
            usage = {
                "prompt_tokens": input_tokens,
                "completion_tokens": output_tokens,
                "total_tokens": input_tokens + output_tokens,
            }
        else:
            return  # No usage info available

        # Set usage in multiple formats for LangSmith compatibility
        run_tree.extra.update(usage)
        run_tree.inputs = {"messages": messages}
        run_tree.outputs = {
            "choices": [{"message": {"content": str(result)}}],
            "usage": usage,
            "model": self.model_name,
        }

    @traceable(run_type="llm", name="instructor_create")
    async def create(self, response_model, messages, **kwargs):
        """Create method with optional LangSmith tracing and token usage reporting."""
        # Try to use create_with_completion to get token usage
        try:
            result, completion = await self.instructor_client.create_with_completion(
                response_model=response_model, messages=messages, **kwargs
            )

            # Report usage to LangSmith only when tracing is enabled
            if is_tracing_enabled():
                try:
                    from langsmith import get_current_run_tree

                    self._report_usage_to_langsmith(
                        get_current_run_tree(), completion, result, messages
                    )

                    # Capture token usage for test tracking
                    try:
                        from vocab_processor.utils.token_tracker import (
                            capture_token_usage_directly,
                        )

                        # Extract token usage directly from completion
                        if hasattr(completion, "usage") and completion.usage:
                            # OpenAI format
                            capture_token_usage_directly(
                                prompt_tokens=completion.usage.prompt_tokens,
                                completion_tokens=completion.usage.completion_tokens,
                                model_name=self.model_name,
                                provider="openai",
                            )
                        elif hasattr(completion, "meta") and completion.meta:
                            # AWS Bedrock format
                            input_tokens = getattr(completion.meta, "input_tokens", 0)
                            output_tokens = getattr(completion.meta, "output_tokens", 0)
                            capture_token_usage_directly(
                                prompt_tokens=input_tokens,
                                completion_tokens=output_tokens,
                                model_name=self.model_name,
                                provider="anthropic",
                            )
                    except Exception:
                        pass

                except Exception:
                    pass

            return result

        except (AttributeError, TypeError):
            # Fallback to regular create method if create_with_completion is not available
            return await self.instructor_client.create(
                response_model=response_model, messages=messages, **kwargs
            )


def get_instructor_node_executor_llm():
    """Get cached instructor client for GPT-4.1-mini with LangSmith tracing."""
    global _instructor_node_executor_llm

    # "gpt-4.1-mini-2025-04-14"  # "gpt-4.1-nano-2025-04-14"
    model_name = "gpt-4.1-2025-04-14"

    if _instructor_node_executor_llm is None:
        base_client = from_openai(
            client=client,
            model=model_name,
            temperature=0.0,
            mode=Mode.JSON,
        )
        _instructor_node_executor_llm = TracedInstructorClient(base_client, model_name)
    return _instructor_node_executor_llm


def get_instructor_supervisor_llm():
    """Get cached supervisor LLM with LangSmith tracing."""
    global _instructor_supervisor_llm

    # "gpt-4.1-2025-04-14"  # "gpt-4.1-mini-2025-04-14"
    model_name = "gpt-4o-2024-08-06"

    if _instructor_supervisor_llm is None:
        base_client = from_openai(
            client=client,
            model=model_name,
            temperature=0.0,
            mode=Mode.JSON,
        )
        _instructor_supervisor_llm = TracedInstructorClient(base_client, model_name)
    return _instructor_supervisor_llm


def get_node_executor_llm():
    """Get cached instructor client for Claude-4 Sonnet via AWS Bedrock with LangSmith tracing."""
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
            temperature=0.0,
            model="us.anthropic.claude-sonnet-4-20250514-v1:0",
        )

        # Wrap synchronous Bedrock client with async interface
        import asyncio

        class AsyncBedrockInstructor:
            """Async wrapper for Bedrock's synchronous instructor client."""

            def __init__(self, sync_client):
                self.sync_client = sync_client

            async def create(self, *args, **kwargs):
                """Async wrapper for create method."""
                return await asyncio.to_thread(self.sync_client.create, *args, **kwargs)

            async def create_with_completion(self, *args, **kwargs):
                """Async wrapper for create_with_completion method."""
                return await asyncio.to_thread(
                    self.sync_client.create_with_completion, *args, **kwargs
                )

        base_client = AsyncBedrockInstructor(sync_instructor_client)
        _instructor_aws_claude4 = TracedInstructorClient(base_client, "claude-sonnet-4")

    return _instructor_aws_claude4


instructor_node_executor_llm = get_instructor_node_executor_llm()
instructor_supervisor_llm = get_instructor_supervisor_llm()
# instructor_aws_claude4 = get_instructor_aws_claude4()


class LLMVariant(str, Enum):
    """Supported LLM back-ends."""

    NODE_EXECUTOR = "node_executor"  # llm for executing node tasks
    SUPERVISOR = "supervisor"  # llm for supervising node tasks


# Map each variant to its cached Instructor client
LLM_PROVIDERS = {
    LLMVariant.NODE_EXECUTOR: instructor_node_executor_llm,
    LLMVariant.SUPERVISOR: instructor_supervisor_llm,
    # LLMVariant.CLAUDE4S: instructor_aws_claude4,
}


def get_llm_client(provider: LLMVariant = LLMVariant.NODE_EXECUTOR):
    """Return the traced Instructor client for the requested provider.

    Args:
        provider: LLMVariant enum member specifying which LLM to use

    Returns:
        TracedInstructorClient: Client with LangSmith tracing and token usage reporting
    """
    return LLM_PROVIDERS[provider]
