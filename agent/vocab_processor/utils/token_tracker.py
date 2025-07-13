"""Token usage tracking utilities for test framework."""

from contextlib import asynccontextmanager
from dataclasses import dataclass, field
from typing import Any, Optional

from vocab_processor.constants import is_tracing_enabled


@dataclass
class TokenUsage:
    """Represents token usage for a single LLM call."""

    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0
    model_name: Optional[str] = None
    provider: Optional[str] = None

    @property
    def input_tokens(self) -> int:
        """Alias for prompt_tokens for consistency."""
        return self.prompt_tokens

    @property
    def output_tokens(self) -> int:
        """Alias for completion_tokens for consistency."""
        return self.completion_tokens


@dataclass
class TestTokenUsage:
    """Aggregated token usage for a complete test case."""

    test_id: str
    total_execution_time: float = 0.0
    total_input_tokens: int = 0
    total_output_tokens: int = 0
    total_tokens: int = 0
    llm_calls: list[TokenUsage] = field(default_factory=list)
    models_used: list[str] = field(default_factory=list)

    def add_llm_call(self, usage: TokenUsage) -> None:
        """Add a single LLM call's token usage to the test totals."""
        self.llm_calls.append(usage)
        self.total_input_tokens += usage.input_tokens
        self.total_output_tokens += usage.output_tokens
        self.total_tokens += usage.total_tokens

        if usage.model_name and usage.model_name not in self.models_used:
            self.models_used.append(usage.model_name)

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "test_id": self.test_id,
            "total_execution_time": self.total_execution_time,
            "total_input_tokens": self.total_input_tokens,
            "total_output_tokens": self.total_output_tokens,
            "total_tokens": self.total_tokens,
            "models_used": self.models_used,
            "llm_calls": [
                {
                    "prompt_tokens": call.prompt_tokens,
                    "completion_tokens": call.completion_tokens,
                    "total_tokens": call.total_tokens,
                    "model_name": call.model_name,
                    "provider": call.provider,
                }
                for call in self.llm_calls
            ],
        }


class TokenTracker:
    """Simple token tracker for sequential test execution."""

    def __init__(self):
        self.current_test_usage: Optional[TestTokenUsage] = None
        self._test_usages: dict[str, TestTokenUsage] = {}

    def start_test(self, test_id: str) -> None:
        """Start tracking tokens for a new test case."""
        self.current_test_usage = TestTokenUsage(test_id=test_id)

    def end_test(self, execution_time: float) -> Optional[TestTokenUsage]:
        """End tracking for current test and return usage data."""
        if self.current_test_usage:
            self.current_test_usage.total_execution_time = execution_time
            self._test_usages[self.current_test_usage.test_id] = self.current_test_usage
            usage = self.current_test_usage
            self.current_test_usage = None
            return usage
        return None

    def capture_langsmith_usage(self) -> None:
        """Capture token usage from current LangSmith run if available."""
        if not is_tracing_enabled() or not self.current_test_usage:
            return

        try:
            from langsmith import get_current_run_tree

            run_tree = get_current_run_tree()

            if run_tree and run_tree.extra:
                # Extract token usage from run_tree.extra
                usage = TokenUsage()

                # Check for token usage in extra fields
                if "prompt_tokens" in run_tree.extra:
                    usage.prompt_tokens = run_tree.extra.get("prompt_tokens", 0)
                if "completion_tokens" in run_tree.extra:
                    usage.completion_tokens = run_tree.extra.get("completion_tokens", 0)
                if "total_tokens" in run_tree.extra:
                    usage.total_tokens = run_tree.extra.get("total_tokens", 0)

                # Get model info
                usage.model_name = run_tree.extra.get("ls_model_name")
                usage.provider = run_tree.extra.get("ls_provider")

                # Only add if we have meaningful token data
                if usage.total_tokens > 0:
                    self.current_test_usage.add_llm_call(usage)

        except Exception:
            # Silently fail if LangSmith is not available or other issues
            pass

    def capture_token_usage_directly(
        self,
        prompt_tokens: int,
        completion_tokens: int,
        model_name: str,
        provider: str = "openai",
    ) -> None:
        """Capture token usage directly without relying on LangSmith run tree."""
        if not self.current_test_usage:
            return

        usage = TokenUsage(
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            total_tokens=prompt_tokens + completion_tokens,
            model_name=model_name,
            provider=provider,
        )

        if usage.total_tokens > 0:
            self.current_test_usage.add_llm_call(usage)

    def get_test_usage(self, test_id: str) -> Optional[TestTokenUsage]:
        """Get token usage for a specific test."""
        return self._test_usages.get(test_id)

    def get_all_usages(self) -> dict[str, TestTokenUsage]:
        """Get all test token usages."""
        return self._test_usages.copy()

    def clear(self) -> None:
        """Clear all tracked usage data."""
        self.current_test_usage = None
        self._test_usages.clear()


# Global token tracker instance
_token_tracker = TokenTracker()


def get_token_tracker() -> TokenTracker:
    """Get the global token tracker instance."""
    return _token_tracker


@asynccontextmanager
async def track_test_tokens(test_id: str):
    """Context manager to track token usage for a test case."""
    tracker = get_token_tracker()
    tracker.start_test(test_id)

    try:
        yield tracker
    finally:
        # Note: execution_time should be set by the caller
        pass


def capture_current_usage() -> None:
    """Capture token usage from the current LangSmith run."""
    tracker = get_token_tracker()
    tracker.capture_langsmith_usage()


def capture_token_usage_directly(
    prompt_tokens: int,
    completion_tokens: int,
    model_name: str,
    provider: str = "openai",
) -> None:
    """Capture token usage directly without relying on LangSmith run tree."""
    tracker = get_token_tracker()
    tracker.capture_token_usage_directly(
        prompt_tokens, completion_tokens, model_name, provider
    )
