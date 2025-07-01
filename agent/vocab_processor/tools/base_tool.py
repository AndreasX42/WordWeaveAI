"""Base tool utilities and common patterns for vocab processor tools."""

from typing import Any, Dict, Type, TypeVar

from aws_lambda_powertools import Logger
from pydantic import BaseModel

from vocab_processor.constants import LLMVariant, get_llm_client

logger = Logger(service="vocab-processor")

T = TypeVar("T", bound=BaseModel)


class SystemMessages:
    """Standard system messages for different tool types."""

    LINGUISTIC_SPECIALIST = (
        "You are a linguistic specialist. Provide accurate, natural responses."
    )
    VALIDATION_SPECIALIST = "You are an expert vocabulary validation assistant. Follow instructions exactly and return only valid JSON responses."
    MEDIA_SPECIALIST = (
        "You are a linguistic specialist. Select and adapt media accurately."
    )


async def create_llm_response(
    response_model: Type[T],
    user_prompt: str,
    system_message: str = SystemMessages.LINGUISTIC_SPECIALIST,
    llm_provider: "LLMVariant | str" = LLMVariant.GPT41M,
    **kwargs
) -> T:
    """
    Standardized LLM response creation with error handling.

    Args:
        response_model: Pydantic model for response validation
        user_prompt: User prompt text
        system_message: System message (defaults to linguistic specialist)
        llm_provider: Identifier of the LLM to use (LLMVariant or matching string value, e.g., "gpt41m", "gpt41", "claude4s")
        **kwargs: Additional parameters for instructor create

    Returns:
        Validated response model instance
    """
    client = get_llm_client(str(llm_provider))

    try:
        return await client.create(
            response_model=response_model,
            messages=[
                {"role": "system", "content": system_message},
                {"role": "user", "content": user_prompt},
            ],
            **kwargs
        )
    except Exception as e:
        logger.error(
            "llm_response_failed",
            response_model=response_model.__name__,
            error=str(e),
            llm_provider=str(llm_provider),
        )
        raise


def create_tool_error_response(
    error: Exception, context: Dict[str, Any]
) -> Dict[str, Any]:
    """
    Create standardized error response for tools.

    Args:
        error: Exception that occurred
        context: Context information for logging

    Returns:
        Standardized error response dictionary
    """
    logger.error("tool_execution_failed", error=str(error), context=context)
    return {
        "error": str(error),
        "message": "An error occurred during tool execution",
        "context": context,
    }
