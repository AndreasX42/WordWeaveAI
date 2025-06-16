import asyncio
import os
from asyncio import TimeoutError
from typing import Any, Dict

from aws_lambda_powertools import Logger, Metrics
from aws_lambda_powertools.metrics import MetricUnit
from aws_lambda_powertools.utilities.batch import (
    AsyncBatchProcessor,
    EventType,
    async_process_partial_response,
)
from aws_lambda_powertools.utilities.parser import parse
from aws_lambda_powertools.utilities.typing import LambdaContext
from pydantic import BaseModel, Field
from vocab_processor.agent import graph

logger = Logger(service="vocab-processor")
metrics = Metrics(namespace="VocabProcessor")

processor = AsyncBatchProcessor(event_type=EventType.SQS)


class VocabProcessRequestDto(BaseModel):
    """Schema for vocabulary processing requests."""

    source_word: str = Field(..., description="The word to process")
    target_language: str = Field(..., description="Target language for translation")
    user_id: str = Field(None, description="Optional user ID for tracking")
    request_id: str = Field(None, description="Optional request ID for tracking")


@logger.inject_lambda_context()
def lambda_handler(event: Dict[str, Any], context: LambdaContext) -> Dict[str, Any]:
    """
    Lambda handler for processing vocabulary requests from SQS.

    This function processes SQS messages containing vocabulary processing requests
    and runs them through the LangGraph agent using async processing.
    """
    return async_process_partial_response(
        event=event,
        record_handler=process_record,
        processor=processor,
        context=context,
    )


async def process_record(record: Dict[str, Any]):
    """
    Process a single SQS record containing a vocabulary processing request.

    Args:
        record: SQS record containing the vocabulary request data
    """
    try:
        # Parse the SQS message body
        vocab_request: VocabProcessRequestDto = parse(
            event=record["body"], model=VocabProcessRequestDto
        )

        logger.info(f"Processing vocab request: {vocab_request}")

        # Add context to logger
        logger.append_keys(
            source_word=vocab_request.source_word,
            target_language=vocab_request.target_language,
            user_id=vocab_request.user_id,
            request_id=vocab_request.request_id,
        )

        logger.info("Starting vocabulary processing from SQS")

        # Set timeout for processing
        timeout_seconds = int(os.getenv("LAMBDA_PROCESSING_TIMEOUT", "90"))

        try:
            # Run the vocab processing with timeout - now using await instead of asyncio.run
            result = await asyncio.wait_for(
                process_vocab_request_and_handle_result(vocab_request),
                timeout=timeout_seconds,
            )

            print(result)

            metrics.add_metric(name="VocabProcessed", unit=MetricUnit.Count, value=1)
            logger.info("Vocabulary processing completed successfully")

        except TimeoutError:
            logger.error(
                f"Vocabulary processing timed out after {timeout_seconds} seconds"
            )
            metrics.add_metric(name="VocabTimeout", unit=MetricUnit.Count, value=1)
            raise

    except Exception as e:
        logger.exception(f"Failed to process vocab record: {e}")
        metrics.add_metric(name="VocabFailed", unit=MetricUnit.Count, value=1)
        raise


async def process_vocab_request_and_handle_result(
    request: VocabProcessRequestDto,
) -> Dict[str, Any]:

    # Process the vocabulary request
    result = await process_vocab_request(request.source_word, request.target_language)

    # Handle the result
    await handle_processing_result(result, request)

    return result


async def process_vocab_request(
    source_word: str, target_language: str
) -> Dict[str, Any]:
    logger.info(
        f"Starting agent processing for word: {source_word} -> {target_language}"
    )

    initial_state = {"source_word": source_word, "target_language": target_language}
    result = await graph.ainvoke(initial_state)
    return result


async def handle_processing_result(
    result: Dict[str, Any], request: VocabProcessRequestDto
):

    try:
        # Example: Log the result (replace with your actual storage logic)
        logger.info(
            "Processing result ready",
            extra={
                "result_keys": list(result.keys()),
                "has_translation": "translation" in result,
                "has_examples": "examples" in result,
                "request_id": request.request_id,
            },
        )

        # TODO: Implement your result handling logic here
        # Examples:

        # 1. Store in DynamoDB
        # await store_result_in_dynamo(result, request)

        # 2. Store in S3
        # await store_result_in_s3(result, request)

        # 3. Call webhook
        # await send_webhook_notification(result, request)

        metrics.add_metric(name="ResultHandled", unit=MetricUnit.Count, value=1)

    except Exception as e:
        logger.exception(f"Failed to handle processing result: {e}")
        metrics.add_metric(name="ResultHandleFailed", unit=MetricUnit.Count, value=1)
        # Don't re-raise here if you want the main processing to be considered successful
        # even if result handling fails


async def store_result_in_dynamo(
    result: Dict[str, Any], request: VocabProcessRequestDto
):
    """Store result in DynamoDB."""
    # Implementation would go here
    pass


async def store_result_in_s3(result: Dict[str, Any], request: VocabProcessRequestDto):
    """Store result in S3."""
    # Implementation would go here
    pass


async def send_webhook_notification(
    result: Dict[str, Any], request: VocabProcessRequestDto
):
    """Send result via webhook."""
    # Implementation would go here
    pass
