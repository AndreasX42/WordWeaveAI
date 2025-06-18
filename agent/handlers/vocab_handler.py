import asyncio
import os
from asyncio import TimeoutError
from typing import Any, Dict

import boto3
from aws_lambda_powertools import Logger, Metrics
from aws_lambda_powertools.metrics import MetricUnit
from aws_lambda_powertools.utilities.batch import (
    AsyncBatchProcessor,
    EventType,
    async_process_partial_response,
)
from aws_lambda_powertools.utilities.parser import parse
from aws_lambda_powertools.utilities.typing import LambdaContext
from vocab_processor.agent import graph
from vocab_processor.constants import Language
from vocab_processor.utils.ddb_utils import VocabProcessRequestDto, exists, store_result

logger = Logger(service="vocab-processor")
metrics = Metrics(namespace="VocabProcessor")

processor = AsyncBatchProcessor(event_type=EventType.SQS)
dynamodb = boto3.resource(
    "dynamodb",
    config=boto3.session.Config(
        max_pool_connections=50, retries={"max_attempts": 3, "mode": "adaptive"}
    ),
)

VOCAB_TABLE = dynamodb.Table(os.environ["DYNAMODB_VOCAB_TABLE_NAME"])
DEFAULT_TIMEOUT = int(os.getenv("LAMBDA_PROCESSING_TIMEOUT", "90"))  # seconds
VISIBILITY_BUFFER = 120  # seconds – keep SQS visibility > Lambda timeout
BATCH_WRITE_RETRIES = 3  # Max retries for batch operations


@logger.inject_lambda_context()
def lambda_handler(event: Dict[str, Any], context: LambdaContext):
    """Entrypoint – invoked by SQS."""
    return async_process_partial_response(
        event=event,
        record_handler=_process_record,
        processor=processor,
        context=context,
    )


async def _process_record(record: Dict[str, Any]):
    """Handle one SQS record."""
    try:
        request: VocabProcessRequestDto = parse(
            event=record["body"], model=VocabProcessRequestDto
        )

        logger.append_keys(
            source_word=request.source_word,
            target_language=request.target_language,
            user=request.user_id,
            req=request.request_id,
        )
        logger.info("received_request")

        try:
            result = await asyncio.wait_for(
                _handle_request(request), timeout=DEFAULT_TIMEOUT
            )
            metrics.add_metric("VocabProcessed", MetricUnit.Count, 1)
            logger.info("request_done", cache_hit=result.get("cache_hit", False))
        except TimeoutError:
            metrics.add_metric("VocabTimeout", MetricUnit.Count, 1)
            logger.error("processing_timeout", seconds=DEFAULT_TIMEOUT)
            raise

    except Exception as exc:
        metrics.add_metric("VocabFailed", MetricUnit.Count, 1)
        logger.exception("record_failed", error=str(exc))
        raise


async def _handle_request(req: VocabProcessRequestDto) -> Dict[str, Any]:
    # Initialize WebSocket notifier for real-time updates
    from vocab_processor.utils.websocket_utils import WebSocketNotifier

    notifier = WebSocketNotifier(user_id=req.user_id, request_id=req.request_id)

    try:
        # Notify ALL subscribers that processing started for this word pair
        notifier.send_processing_started(req.source_word, req.target_language)

        # 1. Validate word and check if already exists
        if await exists(req.source_word, req.target_language):
            cached_result = {
                "status": "cached",
                "source_word": req.source_word,
                "target_language": req.target_language,
                "cache_hit": True,
            }
            # Notify ALL subscribers about cache hit
            notifier.send_cache_hit(req.source_word, req.target_language, cached_result)
            return cached_result

        # 2. Call the graph with streaming
        initial_state = {
            "source_word": req.source_word,
            "target_language": Language.from_code(req.target_language),
        }

        # Stream the graph execution and send real-time updates to ALL subscribers
        result = None
        async for chunk in graph.astream(initial_state, stream_mode="values"):
            print(f"chunk: {chunk}")
            # Send real-time chunk updates to ALL WebSocket subscribers for this word pair
            notifier.send_chunk_update(req.source_word, req.target_language, chunk)
            result = chunk  # Keep the last chunk as final result

        logger.info("result", result=result)

        # 3. Persist the result to DynamoDB
        await store_result(result, req)

        # Notify ALL subscribers that processing completed
        notifier.send_processing_completed(req.source_word, req.target_language, result)

        return result

    except Exception as e:
        # Notify ALL subscribers that processing failed
        notifier.send_processing_failed(req.source_word, req.target_language, str(e))
        raise
