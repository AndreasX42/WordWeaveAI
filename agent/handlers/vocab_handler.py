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
from vocab_processor.utils.ddb_utils import (
    VocabProcessRequestDto,
    store_result,
    validate_and_check_exists,
)
from vocab_processor.utils.websocket_utils import WebSocketNotifier

# Constants
DEFAULT_TIMEOUT = int(os.getenv("LAMBDA_PROCESSING_TIMEOUT", "90"))
VISIBILITY_BUFFER = 120
BATCH_WRITE_RETRIES = 1
DDB_MAX_POOL_CONNECTIONS = 50
DDB_MAX_RETRY_ATTEMPTS = 3

# Status constants
STATUS_INVALID = "invalid"
STATUS_EXISTS = "exists"
STATUS_NOT_EXISTS = "not_exists"

logger = Logger(service="vocab-processor")
metrics = Metrics(namespace="VocabProcessor")

processor = AsyncBatchProcessor(event_type=EventType.SQS)
dynamodb = boto3.resource(
    "dynamodb",
    config=boto3.session.Config(
        max_pool_connections=DDB_MAX_POOL_CONNECTIONS,
        retries={"max_attempts": DDB_MAX_RETRY_ATTEMPTS, "mode": "adaptive"},
    ),
)


@logger.inject_lambda_context()
def lambda_handler(event: Dict[str, Any], context: LambdaContext):
    """Entrypoint for the Vocab Processor Lambda."""
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
            logger.info("request_done", ddb_hit=result.get("ddb_hit", False))
        except TimeoutError:
            metrics.add_metric("VocabTimeout", MetricUnit.Count, 1)
            logger.error("processing_timeout", seconds=DEFAULT_TIMEOUT)
            raise

    except Exception as exc:
        metrics.add_metric("VocabFailed", MetricUnit.Count, 1)
        logger.exception("record_failed", error=str(exc))
        raise


async def _handle_request(req: VocabProcessRequestDto) -> Dict[str, Any]:
    """Main request handler."""
    notifier = WebSocketNotifier(user_id=req.user_id, request_id=req.request_id)

    try:
        # Notify all subscribers that processing started for this vocabulary word
        notifier.send_processing_started(req.source_word, req.target_language)

        # Check if word is valid and already exists
        validation_result = await _validate_word(req, notifier)
        if validation_result is not None:
            return validation_result

        # Process the word with the graph
        result = await _process_word_with_graph(req, notifier)

        # Store and notify completion
        await store_result(result, req)
        notifier.send_processing_completed(req.source_word, req.target_language, result)

        return result

    except Exception as e:
        notifier.send_processing_failed(req.source_word, req.target_language, str(e))
        raise


async def _validate_word(
    req: VocabProcessRequestDto, notifier: WebSocketNotifier
) -> Dict[str, Any] | None:
    """Validate word and check if it exists. Returns result dict if processing should stop, None to continue."""
    check_result = await validate_and_check_exists(req.source_word, req.target_language)

    if check_result["status"] == STATUS_INVALID:
        logger.warning(
            "word_validation_failed",
            word=req.source_word,
            target_lang=req.target_language,
            reason=getattr(check_result["validation_result"], "message", "unknown"),
        )
        notifier.send_validation_failed(
            req.source_word, req.target_language, check_result["validation_result"]
        )
        return {
            "status": STATUS_INVALID,
            "source_word": req.source_word,
            "target_language": req.target_language,
            "validation_result": check_result["validation_result"],
        }

    elif check_result["status"] == STATUS_EXISTS:
        logger.info(
            "word_already_exists",
            word=req.source_word,
            target_lang=req.target_language,
        )
        ddb_result = {
            "status": STATUS_EXISTS,
            "source_word": req.source_word,
            "target_language": req.target_language,
            "result": check_result["existing_item"],
            "ddb_hit": True,
        }
        notifier.send_ddb_hit(req.source_word, req.target_language, ddb_result)
        return ddb_result

    # Word is valid and doesn't exist - continue processing
    logger.info(
        "word_validation_passed",
        word=req.source_word,
        target_lang=req.target_language,
        source_lang=check_result["validation_result"].source_language,
    )
    return None


async def _process_word_with_graph(
    req: VocabProcessRequestDto, notifier: WebSocketNotifier
) -> Dict[str, Any]:
    """Process the word using the vocab processing graph."""
    initial_state = {
        "source_word": req.source_word,
        "target_language": Language.from_code(req.target_language),
    }

    # Stream the graph execution and send real-time updates
    result = None
    async for chunk in graph.astream(initial_state, stream_mode="values"):
        logger.info("chunk", chunk=chunk)
        notifier.send_chunk_update(req.source_word, req.target_language, chunk)
        result = chunk  # Keep the last chunk as final result

    logger.info("result", result=result)
    return result
