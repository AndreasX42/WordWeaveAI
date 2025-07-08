import asyncio
import os
import re
import unicodedata
from datetime import datetime, timezone
from decimal import ROUND_HALF_UP, Decimal
from typing import Any, Dict

import boto3
from aws_lambda_powertools import Logger
from aws_lambda_powertools.metrics import Metrics, MetricUnit
from botocore.exceptions import ClientError
from pydantic import BaseModel, Field

logger = Logger(service="vocab-processor")
metrics = Metrics(namespace="VocabProcessor")

dynamodb = boto3.resource(
    "dynamodb",
    region_name=os.getenv("AWS_REGION", "us-east-1"),
    config=boto3.session.Config(
        max_pool_connections=50, retries={"max_attempts": 3, "mode": "adaptive"}
    ),
)
VOCAB_TABLE = dynamodb.Table(os.getenv("DYNAMODB_VOCAB_TABLE_NAME"))

_NORMALISE_RGX = re.compile(r"[^a-z0-9]")


def is_lambda_context() -> bool:
    """
    Check if we're running in AWS Lambda context.

    Returns:
        True if running in Lambda, False if running locally (e.g., langgraph dev)
    """
    return os.getenv("AWS_LAMBDA_FUNCTION_NAME") is not None


def normalize_word(word: str) -> str:
    """Return lowercase, accent stripped, alnumonly version of the word."""
    word = unicodedata.normalize("NFKC", word.lower())
    word = "".join(
        ch
        for ch in unicodedata.normalize("NFD", word)
        if unicodedata.category(ch) != "Mn"
    )
    return _NORMALISE_RGX.sub("", word)


class VocabProcessRequestDto(BaseModel):
    source_word: str = Field(..., description="Word to process")
    source_language: str | None = Field(
        None,
        description="Source language (ISO code). If not provided, it will be detected by the validation step.",
    )
    target_language: str = Field(..., description="Target language (ISO code)")
    user_id: str | None = Field(None)
    request_id: str | None = Field(None)


def lang_code(lang_enum) -> str:
    """Return iso code for Language enum, falling back to .value."""
    return getattr(lang_enum, "code", str(lang_enum.value).lower())


async def get_existing_media_for_search_words(
    search_words: list[str],
) -> Dict[str, Any] | None:
    """Return the first Media object found for any of *search_words*.

    The function fires all GSI look-ups concurrently (one per word) and returns
    as soon as the *first* task comes back with a hit.  Because **all** items
    – main vocabulary rows *and* SEARCH# fan-out rows – carry the same
    ``english_word`` attribute and are projected into the
    ``EnglishMediaLookupIndex`` GSI, a single query per word is sufficient.
    """

    if not is_lambda_context():
        logger.info(
            f"Local dev mode: skipping DynamoDB media lookup for search words: {search_words}"
        )
        return None

    async def _query_gsi(word: str):
        norm = normalize_word(word)
        try:
            resp = await asyncio.to_thread(
                VOCAB_TABLE.query,
                IndexName="EnglishMediaLookupIndex",
                KeyConditionExpression="english_word = :w",
                ExpressionAttributeValues={":w": norm},
                ProjectionExpression="media",
                Limit=1,
            )
            items = resp.get("Items", [])
            if items and items[0].get("media"):
                media = items[0]["media"]
                logger.info(
                    "existing_media_hit",
                    matched_word=word,
                )
                # Attach bookkeeping fields so caller can log which word hit
                media_copy = dict(media)  # shallow copy – DDB types are JSON-safe
                media_copy["matched_word"] = word
                return media_copy
        except Exception as exc:
            logger.warning("english_media_lookup_failed", word=word, error=str(exc))
        return None

    # Fire all queries concurrently and return on first hit
    tasks = [asyncio.create_task(_query_gsi(w)) for w in search_words]

    # Use asyncio.as_completed for early termination on first hit
    for coro in asyncio.as_completed(tasks):
        result = await coro
        if result:
            # Cancel remaining tasks to save resources
            for task in tasks:
                if not task.done():
                    task.cancel()
            return result

    logger.info("no_media_for_search_words", words=search_words)
    return None


def to_ddb(value: Any):
    """Recursively convert *value* to something DynamoDB can store."""
    if value is None or isinstance(value, (bool, str)):
        return value
    if isinstance(value, (int, Decimal)):
        return Decimal(value)
    if isinstance(value, float):
        return Decimal(str(value)).quantize(Decimal("0.0001"), rounding=ROUND_HALF_UP)
    if isinstance(value, list):
        return [to_ddb(v) for v in value]
    if isinstance(value, dict):
        return {k: to_ddb(v) for k, v in value.items() if v is not None}

    # Handle objects with model_dump (Pydantic), __dict__, or value (Enum)
    for attr in ("model_dump", "__dict__", "value"):
        if hasattr(value, attr):
            obj_value = getattr(value, attr)
            return to_ddb(obj_value() if callable(obj_value) else obj_value)

    return str(value)


async def validate_and_check_exists(
    src_word: str, tgt_lang: str, src_lang: str | None = None
) -> Dict[str, Any]:
    """
    Validate word and check if it exists in DDB.

    Returns:
        Dict with keys:
        - 'status': 'invalid' | 'exists' | 'not_exists'
        - 'validation_result': ValidationResult object
        - 'existing_item': DDB item if exists, else None
    """
    from vocab_processor.constants import Language
    from vocab_processor.tools.validation_tool import validate_word

    validation_result = await validate_word.ainvoke(
        input={
            "source_word": src_word,
            "target_language": Language.from_code(tgt_lang),
            "source_language": Language.from_code(src_lang) if src_lang else None,
        }
    )

    if not validation_result.is_valid:
        logger.warning(
            "invalid_word",
            word=src_word,
            tgt_lang=tgt_lang,
            reason=getattr(validation_result, "message", "unknown"),
        )
        return {
            "status": "invalid",
            "validation_result": validation_result,
            "existing_item": None,
        }

    if not is_lambda_context():
        logger.info(
            f"Local dev mode: skipping DynamoDB existence check for {src_word} -> {tgt_lang}"
        )
        return {
            "status": "not_exists",
            "validation_result": validation_result,
            "existing_item": None,
        }

    pk = (
        f"SRC#{lang_code(validation_result.source_language)}#{normalize_word(src_word)}"
    )
    # Query for any translation to target language (regardless of POS)
    sk_prefix = f"TGT#{tgt_lang}"

    response = await asyncio.to_thread(
        VOCAB_TABLE.query,
        KeyConditionExpression="PK = :pk AND begins_with(SK, :sk_prefix)",
        ExpressionAttributeValues={":pk": pk, ":sk_prefix": sk_prefix},
        Limit=1,
    )
    items = response.get("Items", [])
    existing_item = items[0] if items else None

    if existing_item:
        logger.info("ddb_hit", pk=pk, sk=existing_item["SK"])
        return {
            "status": "exists",
            "validation_result": validation_result,
            "existing_item": existing_item,
        }

    return {
        "status": "not_exists",
        "validation_result": validation_result,
        "existing_item": None,
    }


async def store_result(result: Dict[str, Any], req: VocabProcessRequestDto):
    src_lang = result.get("source_language")
    tgt_lang = result.get("target_language")
    src_word = result.get("source_word")
    tgt_word = result.get("target_word")

    if not all([src_lang, tgt_lang, src_word, tgt_word]):
        raise ValueError("Pipeline result missing mandatory fields")

    if not is_lambda_context():
        logger.info(
            f"Local dev mode: skipping DynamoDB storage for {src_word} -> {tgt_word} ({lang_code(src_lang)} -> {lang_code(tgt_lang)})"
        )
        return

    pk = f"SRC#{lang_code(src_lang)}#{normalize_word(src_word)}"
    source_pos = getattr(result.get("source_part_of_speech"), "value", "unknown")

    # in case of "masculine noun" or "feminine noun", we want to store it as "noun"
    if len(source_pos.split(" ")) == 2:
        source_pos = "noun"

    sk = f"TGT#{lang_code(tgt_lang)}#POS#{source_pos}"

    # Prepare search words for individual entries
    search_query = result.get("search_query", [])
    normalized_search_words = [
        normalize_word(word) for word in search_query if word.strip()
    ]

    item: Dict[str, Any] = {
        "PK": pk,
        "SK": sk,
        # Source word
        "source_word": src_word,
        "source_language": lang_code(src_lang),
        "source_article": result.get("source_article"),
        "source_pos": getattr(result.get("source_part_of_speech"), "value", None),
        "source_definition": result.get("source_definition"),
        # Target word
        "target_word": tgt_word,
        "target_language": lang_code(tgt_lang),
        "target_pos": getattr(result.get("target_part_of_speech"), "value", None),
        "target_article": result.get("target_article"),
        # Additional fields
        "source_additional_info": result.get("source_additional_info"),
        "target_additional_info": result.get("target_additional_info"),
        "target_syllables": result.get("target_syllables"),
        "target_phonetic_guide": result.get("target_phonetic_guide"),
        "synonyms": to_ddb(result.get("synonyms")),
        "examples": to_ddb(result.get("examples")),
        "conjugation_table": to_ddb(result.get("conjugation")),
        "pronunciations": result.get("pronunciations"),
        "media": to_ddb(result.get("media")),
        # GSI-1: Reverse lookup
        "LKP": f"LKP#{lang_code(tgt_lang)}#{normalize_word(tgt_word)}",
        "SRC_LANG": f"SRC#{lang_code(src_lang)}",
        # GSI-2: English word lookup for Media reuse
        "english_word": normalize_word(result.get("english_word", "")),
        # Metadata
        "schema_version": 1,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "created_by": req.user_id or "anonymous",
    }

    item = {k: v for k, v in item.items() if v not in (None, [], "")}

    try:
        # Store the main item
        await asyncio.to_thread(
            VOCAB_TABLE.put_item,
            Item=item,
            ConditionExpression="attribute_not_exists(PK) and attribute_not_exists(SK)",
        )
        logger.info("ddb_put_ok", pk=pk, sk=sk, search_words=normalized_search_words)
        metrics.add_metric("VocabStored", MetricUnit.Count, 1)

        # Store additional entries for each search word (for efficient lookup)
        if (
            normalized_search_words
            and result.get("media")
            and not result.get("media_reused", False)
        ):
            await _store_search_word_entries(
                pk, sk, normalized_search_words, result, req
            )
    except ClientError as err:
        if err.response["Error"].get("Code") == "ConditionalCheckFailedException":
            logger.info("duplicate_write_ignored", pk=pk, sk=sk)
        else:
            logger.exception("ddb_put_failed", err=str(err))
            metrics.add_metric("VocabStoreFailed", MetricUnit.Count, 1)
            raise


async def _store_search_word_entries(
    main_pk: str,
    main_sk: str,
    search_words: list[str],
    result: Dict[str, Any],
    req: VocabProcessRequestDto,
):
    """Store additional entries for each search word to enable efficient media lookup."""

    async def _batch_write(words: list[str]):
        def _sync_write():
            with VOCAB_TABLE.batch_writer() as bw:
                for w in words:
                    bw.put_item(
                        Item={
                            "PK": f"SEARCH#{w}",
                            "SK": f"REF#{main_pk}#{main_sk}",
                            "english_word": w,
                            "media": to_ddb(result.get("media")),
                            "reference_pk": main_pk,
                            "reference_sk": main_sk,
                            "schema_version": 1,
                            "created_at": datetime.now(timezone.utc).isoformat(),
                        }
                    )

        await asyncio.to_thread(_sync_write)
        logger.debug("search_word_entries_stored", count=len(words))

    if search_words:
        await _batch_write(search_words)
