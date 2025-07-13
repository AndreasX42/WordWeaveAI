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

from vocab_processor.agent import graph
from vocab_processor.constants import Language
from vocab_processor.utils.ddb_utils import VocabProcessRequestDto, store_result
from vocab_processor.utils.websocket_utils import WebSocketNotifier

# Constants
DEFAULT_TIMEOUT = int(os.getenv("LAMBDA_PROCESSING_TIMEOUT", "90"))

logger = Logger(service="vocab-processor")
metrics = Metrics(namespace="VocabProcessor")

processor = AsyncBatchProcessor(event_type=EventType.SQS)


@logger.inject_lambda_context()
def lambda_handler(event: Dict[str, Any], context: LambdaContext) -> Dict[str, Any]:
    """Entrypoint for the Vocab Processor Lambda."""
    return async_process_partial_response(
        event=event,
        record_handler=_process_record,
        processor=processor,
        context=context,
    )


async def _process_record(record: Dict[str, Any]) -> None:
    """Handle one SQS record."""
    try:
        request: VocabProcessRequestDto = parse(
            event=record["body"], model=VocabProcessRequestDto
        )

        logger.append_keys(
            source_word=request.source_word,
            target_language=request.target_language,
            source_language=request.source_language,
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

        # Process the word with the graph
        result = await _process_word_with_graph(req, notifier)

        # Evaluate final state and handle different outcomes
        final_result = await _evaluate_final_state(result, req, notifier)

        return final_result

    except Exception as e:
        notifier.send_processing_failed(req.source_word, req.target_language, str(e))
        raise


async def _evaluate_final_state(
    result: Dict[str, Any], req: VocabProcessRequestDto, notifier: WebSocketNotifier
) -> Dict[str, Any]:
    """Evaluate the final graph state and send appropriate notifications."""

    # Check if validation failed
    if result.get("validation_passed") is False:
        logger.warning(
            "word_validation_failed",
            word=req.source_word,
            target_lang=req.target_language,
            source_lang=req.source_language,
            reason=result.get("validation_message", "unknown"),
        )

        validation_result = _build_validation_result(result)
        notifier.send_validation_failed(
            req.source_word, req.target_language, validation_result
        )

        return _build_error_response(
            "invalid", req, validation_result=validation_result
        )

    # Check if word already exists
    if result.get("word_exists") is True:
        logger.info(
            "word_already_exists",
            word=result.get("source_word", req.source_word),
            target_lang=req.target_language,
            source_lang=req.source_language,
        )

        ddb_result = _build_ddb_hit_response(result, req)
        notifier.send_ddb_hit(
            result.get("source_word", req.source_word), req.target_language, ddb_result
        )

        return ddb_result

    # Normal processing completed successfully
    if result.get("processing_complete") or _is_processing_complete(result):
        await store_result(result, req)
        notifier.send_processing_completed(req.source_word, req.target_language, result)
        return result

    # If we get here, something unexpected happened
    logger.warning("unexpected_final_state", result_keys=list(result.keys()))
    notifier.send_processing_failed(
        req.source_word, req.target_language, "Unexpected processing state"
    )

    return _build_error_response("failed", req, error="Unexpected processing state")


def _build_validation_result(result: Dict[str, Any]) -> Dict[str, Any]:
    """Build validation result object for notifications."""
    return {
        "is_valid": False,
        "message": result.get("validation_message"),
        "suggestions": result.get("suggested_words", []),
        "source_language": result.get("source_language"),
    }


def _build_ddb_hit_response(
    result: Dict[str, Any], req: VocabProcessRequestDto
) -> Dict[str, Any]:
    """Build DDB hit response object."""
    return {
        "status": "exists",
        "source_word": result.get("source_word", req.source_word),
        "target_language": req.target_language,
        "source_language": req.source_language,
        "result": result.get("existing_item", {}),
        "ddb_hit": True,
    }


def _build_error_response(
    status: str,
    req: VocabProcessRequestDto,
    error: str = None,
    validation_result: Dict[str, Any] = None,
) -> Dict[str, Any]:
    """Build standardized error response."""
    response = {
        "status": status,
        "source_word": req.source_word,
        "target_language": req.target_language,
        "source_language": req.source_language,
    }

    if error:
        response["error"] = error
    if validation_result:
        response["validation_result"] = validation_result

    return response


def _is_processing_complete(result: Dict[str, Any]) -> bool:
    """Check if processing is complete based on essential fields."""
    required_fields = [
        "source_word",
        "target_word",
        "source_language",
        "target_language",
    ]
    return all(result.get(field) for field in required_fields)


async def _process_word_with_graph(
    req: VocabProcessRequestDto, notifier: WebSocketNotifier
) -> Dict[str, Any]:
    """Process the word using the vocab processing graph."""
    initial_state = {
        "source_word": req.source_word,
        "target_language": Language.from_code(req.target_language),
        "user_id": req.user_id,
        "request_id": req.request_id,
    }

    # Add source_language to initial state if provided
    if req.source_language:
        initial_state["source_language"] = Language.from_code(req.source_language)

    # Stream the graph execution and send real-time updates
    result = None
    async for chunk in graph.astream(initial_state, stream_mode="values"):
        logger.debug("graph_chunk", chunk_keys=list(chunk.keys()) if chunk else [])
        notifier.send_chunk_update(req.source_word, req.target_language, chunk)
        result = chunk  # Keep the last chunk as final result

    logger.info("graph_completed", result_keys=list(result.keys()) if result else [])
    return result
