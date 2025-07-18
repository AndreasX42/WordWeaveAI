import asyncio
import os
from datetime import datetime, timezone
from decimal import ROUND_HALF_UP, Decimal
from typing import Any

import boto3
from aws_lambda_powertools import Logger
from aws_lambda_powertools.metrics import Metrics, MetricUnit
from botocore.exceptions import ClientError
from pydantic import BaseModel, Field

from vocab_processor.constants import PartOfSpeech
from vocab_processor.utils.core_utils import is_lambda_context, normalize_word

logger = Logger(service="vocab-processor")
metrics = Metrics(namespace="VocabProcessor")

dynamodb = boto3.resource(
    "dynamodb",
    region_name=os.getenv("AWS_REGION", "us-east-1"),
    config=boto3.session.Config(
        max_pool_connections=50, retries={"max_attempts": 3, "mode": "adaptive"}
    ),
)

# Lazy initialization to avoid import-time errors during testing
_vocab_table = None
_media_table = None


def get_vocab_table():
    """Get vocab table instance."""
    global _vocab_table
    if _vocab_table is None:
        table_name = os.getenv("DYNAMODB_VOCAB_TABLE_NAME")
        if not table_name:
            raise ValueError("DYNAMODB_VOCAB_TABLE_NAME environment variable not set")
        _vocab_table = dynamodb.Table(table_name)
    return _vocab_table


def get_media_table():
    """Get media table instance."""
    global _media_table
    if _media_table is None:
        try:
            table_name = os.getenv("DYNAMODB_VOCAB_MEDIA_TABLE_NAME")
            if not table_name:
                raise ValueError(
                    "DYNAMODB_VOCAB_MEDIA_TABLE_NAME environment variable not set"
                )
            _media_table = dynamodb.Table(table_name)
        except Exception as exc:
            logger.error("media_table_connection_failed", error=str(exc))
            raise
    return _media_table


class VocabProcessRequestDto(BaseModel):
    source_word: str = Field(..., description="Word to process")
    source_language: str | None = Field(
        None,
        description="Source language (ISO code). If not provided, it will be detected by the validation step.",
    )
    target_language: str = Field(..., description="Target language (ISO code)")
    user_id: str | None = Field(None)
    request_id: str | None = Field(None)

    def model_post_init(self, __context):
        """Validate language codes after initialization."""
        from vocab_processor.constants import Language

        # Validate target_language (required)
        if self.target_language:
            valid_codes = [lang.code for lang in Language]
            if self.target_language not in valid_codes:
                raise ValueError(
                    f"Invalid target_language '{self.target_language}'. Must be one of: {valid_codes}"
                )

        # Validate source_language (optional)
        if self.source_language:
            valid_codes = [lang.code for lang in Language]
            if self.source_language not in valid_codes:
                raise ValueError(
                    f"Invalid source_language '{self.source_language}'. Must be one of: {valid_codes}"
                )

        # Validate source_word is not empty
        if not self.source_word or not self.source_word.strip():
            raise ValueError("source_word cannot be empty")


def lang_code(lang_enum) -> str:
    """Return iso code for Language enum, falling back to .value."""
    return getattr(lang_enum, "code", str(lang_enum.value).lower())


def _get_pos_category(part_of_speech_value: str) -> str:
    """Get the category of a part-of-speech value."""
    return PartOfSpeech(part_of_speech_value).category


async def check_word_exists(
    base_word: str, source_language, target_language: str, source_part_of_speech: str
) -> dict[str, Any]:
    """Check if a word exists in DDB after base word extraction."""
    if not is_lambda_context():
        logger.info(
            f"Local dev mode: skipping DynamoDB existence check for {base_word} -> {target_language}"
        )
        return {"exists": False, "existing_item": None}

    # Extract the part-of-speech value if it's an enum
    if hasattr(source_part_of_speech, "value"):
        pos_value = source_part_of_speech.value
    else:
        pos_value = str(source_part_of_speech)

    # Normalize part-of-speech the same way it's normalized during storage
    normalized_pos = _get_pos_category(pos_value)

    pk = f"SRC#{lang_code(source_language)}#{normalize_word(base_word)}"
    sk = f"TGT#{target_language}#POS#{normalized_pos}"

    logger.info(
        "existence_check_attempt",
        base_word=base_word,
        source_language=lang_code(source_language),
        target_language=target_language,
        original_pos=pos_value,
        normalized_pos=normalized_pos,
        pk=pk,
        sk=sk,
        table_name=get_vocab_table().name,
        aws_region=os.getenv("AWS_REGION", "us-east-1"),
    )

    try:
        response = await asyncio.to_thread(
            get_vocab_table().query,
            KeyConditionExpression="PK = :pk AND SK = :sk",
            ExpressionAttributeValues={":pk": pk, ":sk": sk},
        )

        items = response.get("Items", [])
        existing_item = items[0] if items else None  # type: ignore

        if existing_item:
            logger.info("ddb_hit", pk=pk, sk=sk)
            return {"exists": True, "existing_item": existing_item}

        logger.info("ddb_miss", pk=pk, sk=sk, items_count=len(items))
        return {"exists": False, "existing_item": None}

    except Exception as exc:
        logger.error("existence_check_failed", error=str(exc), pk=pk, sk=sk)
        return {"exists": False, "existing_item": None}


async def get_existing_media_for_search_words(
    search_words: list[str],
) -> dict[str, Any] | None:
    """
    Get existing media for search words using the dedicated media table.

    This function uses the separate media table to find matching search terms,
    then selects the best match based on search term frequency and recency.
    """
    if not is_lambda_context():
        logger.info(
            f"Local dev mode: skipping media lookup for search words: {search_words}"
        )
        return None

    if not search_words:
        return None

    # Normalize all search words
    normalized_words = [normalize_word(word) for word in search_words]

    try:
        media_table = get_media_table()

        # Query each search term individually from the media table
        async def _query_search_term(word: str):
            try:
                response = await asyncio.to_thread(
                    media_table.get_item,
                    Key={"PK": f"SEARCH#{word}"},
                    ProjectionExpression="media_ref, search_term, usage_count, last_used",
                )
                return response.get("Item")
            except Exception as exc:
                logger.warning(
                    "media_search_term_lookup_failed", word=word, error=str(exc)
                )
                return None

        # Fire all queries concurrently
        tasks = [
            asyncio.create_task(_query_search_term(word)) for word in normalized_words
        ]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        # Filter out None results and exceptions
        items = [
            item
            for item in results
            if item is not None and not isinstance(item, Exception)
        ]

        if not items:
            return None

        # Find the best match based on usage frequency and recency
        best_match = None
        best_score = 0

        for item in items:
            # Score based on usage count (higher is better) and recency
            usage_count = int(item.get("usage_count", 0))
            last_used = item.get("last_used", "2020-01-01")

            # Simple scoring: usage_count * recency_factor
            hours_since_last_used = (
                datetime.now(timezone.utc) - datetime.fromisoformat(last_used)
            ).total_seconds() / 3600
            # More recent = higher factor (1.0 for 1 hour ago, 0.5 for 2 hours ago, etc.)
            recency_factor = 1.0 / max(1.0, hours_since_last_used)
            score = usage_count * recency_factor

            if score > best_score:
                best_score = score
                best_match = item

        if best_match:
            media_ref = best_match["media_ref"]
            search_term = best_match["search_term"]

            # Fetch the actual media object from the media table
            media_response = await asyncio.to_thread(
                media_table.get_item,
                Key={"PK": media_ref},
                ProjectionExpression="media",
            )

            media_item = media_response.get("Item")
            if media_item and media_item.get("media"):
                media = media_item["media"]  # type: ignore
                media_copy = dict(media)
                media_copy["matched_word"] = search_term
                media_copy["media_ref"] = media_ref

                # Update usage statistics
                await _update_search_term_usage_media_table(f"SEARCH#{search_term}")

                logger.info(
                    "media_hit",
                    matched_word=search_term,
                    usage_count=usage_count,
                    score=best_score,
                )

                return media_copy

    except Exception as exc:
        logger.warning("media_lookup_failed", error=str(exc))

    return None


async def _update_search_term_usage_media_table(search_term_pk: str):
    """Update usage statistics for a search term in the media table."""
    try:
        media_table = get_media_table()
        await asyncio.to_thread(
            media_table.update_item,
            Key={"PK": search_term_pk},
            UpdateExpression="ADD usage_count :inc SET last_used = :now",
            ExpressionAttributeValues={
                ":inc": 1,
                ":now": datetime.now(timezone.utc).isoformat(),
            },
            ReturnValues="NONE",
        )
    except Exception as exc:
        logger.warning(
            "media_search_term_usage_update_failed", pk=search_term_pk, error=str(exc)
        )


async def store_media_references(
    media_ref: str, search_words: list[str], media_data: dict[str, Any]
):
    """
    Store media references using the separate media table.

    This creates:
    1. One main media entry in media table: PK=MEDIA#{hash}
    2. Multiple search term entries in media table: PK=SEARCH#{word}
    """

    if not search_words or not media_data:
        return

    try:
        media_table = get_media_table()

        # Store the main media entry in the media table
        await asyncio.to_thread(
            media_table.put_item,
            Item={
                "PK": media_ref,
                "media": to_ddb(media_data),
                "created_at": datetime.now(timezone.utc).isoformat(),
                "schema_version": 1,
                "item_type": "media",
            },
            ConditionExpression="attribute_not_exists(PK)",
        )

        # Store search term references (with usage tracking) in the media table
        async def _store_search_term_ref(word: str):
            normalized_word = normalize_word(word)
            await asyncio.to_thread(
                media_table.update_item,
                Key={"PK": f"SEARCH#{normalized_word}"},
                UpdateExpression="SET media_ref = :ref, search_term = :term, last_used = :now, item_type = :type ADD usage_count :inc",
                ExpressionAttributeValues={
                    ":ref": media_ref,
                    ":term": normalized_word,
                    ":now": datetime.now(timezone.utc).isoformat(),
                    ":type": "search_term",
                    ":inc": 1,
                },
                ReturnValues="NONE",
            )

        # Store all search term references concurrently
        await asyncio.gather(
            *[_store_search_term_ref(word) for word in search_words],
            return_exceptions=True,
        )

        logger.info(
            "media_stored",
            media_ref=media_ref,
            search_words=search_words,
            table_name=media_table.name,
        )

    except ClientError as err:
        if err.response["Error"].get("Code") == "ConditionalCheckFailedException":
            logger.info("duplicate_media_ignored", media_ref=media_ref)
        else:
            logger.exception("media_storage_failed", err=str(err))
            raise
    except Exception as exc:
        logger.exception("media_storage_error", error=str(exc))
        raise


async def store_result(result: dict[str, Any], req: VocabProcessRequestDto):
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

    # Handle source_part_of_speech - could be enum, string, or None
    source_pos_raw = result.get("source_part_of_speech")
    if hasattr(source_pos_raw, "value"):
        source_pos = source_pos_raw.value
    elif isinstance(source_pos_raw, str):
        source_pos = source_pos_raw
    else:
        raise ValueError(f"Invalid source_part_of_speech: {source_pos_raw}")

    normalized_pos = _get_pos_category(source_pos)

    sk = f"TGT#{lang_code(tgt_lang)}#POS#{normalized_pos}"

    # Prepare search words for individual entries
    search_query = result.get("search_query", [])
    normalized_search_words = [
        normalize_word(word) for word in search_query if word.strip()
    ]

    item: dict[str, Any] = {
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
        # Store media reference instead of full media object
        "media_ref": result.get("media_ref"),  # Reference to media table
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
            get_vocab_table().put_item,
            Item=item,
            ConditionExpression="attribute_not_exists(PK) and attribute_not_exists(SK)",
        )
        logger.info("ddb_put_ok", pk=pk, sk=sk, search_words=normalized_search_words)
        metrics.add_metric("VocabStored", MetricUnit.Count, 1)

        # Store media in separate table if new media was fetched or adapted to a new language
        media_adapted = result.get("media_adapted", False)
        media_reused = result.get("media_reused", False)
        has_media = result.get("media") is not None

        needs_storage = has_media and (not media_reused or media_adapted)

        if needs_storage:
            media_ref = result.get("media_ref")

            if media_ref:
                await store_media_references(
                    media_ref, normalized_search_words, result.get("media")
                )
    except ClientError as err:
        if err.response["Error"].get("Code") == "ConditionalCheckFailedException":
            logger.info("duplicate_write_ignored", pk=pk, sk=sk)
        else:
            logger.exception("ddb_put_failed", err=str(err))
            metrics.add_metric("VocabStoreFailed", MetricUnit.Count, 1)
            raise


async def get_media_usage_statistics() -> dict[str, Any]:
    """
    Get usage statistics for media reuse optimization from the media table.

    Returns:
        Dict containing usage statistics, top search terms, and reuse rates.
    """
    if not is_lambda_context():
        logger.info("Local dev mode: returning mock media statistics")
        return {
            "total_media_objects": 100,
            "total_search_terms": 500,
            "average_reuse_rate": 0.65,
            "top_search_terms": [
                {"term": "dog", "usage_count": 25},
                {"term": "house", "usage_count": 20},
                {"term": "food", "usage_count": 18},
            ],
        }

    try:
        media_table = get_media_table()

        # Get search term statistics
        search_term_stats = []
        paginator = media_table.scan(
            FilterExpression="item_type = :type",
            ExpressionAttributeValues={":type": "search_term"},
            ProjectionExpression="search_term, usage_count, last_used",
        )

        total_search_terms = 0
        total_usage = 0

        for page in paginator:
            items = page.get("Items", [])
            total_search_terms += len(items)

            for item in items:
                usage_count = int(item.get("usage_count", 0))
                total_usage += usage_count

                search_term_stats.append(
                    {
                        "term": item.get("search_term", ""),
                        "usage_count": usage_count,
                        "last_used": item.get("last_used", ""),
                    }
                )

        # Sort by usage count
        search_term_stats.sort(key=lambda x: x["usage_count"], reverse=True)  # type: ignore

        # Get media object count
        media_paginator = media_table.scan(
            FilterExpression="item_type = :type",
            ExpressionAttributeValues={":type": "media"},
            Select="COUNT",
        )

        total_media_objects = 0
        for page in media_paginator:
            total_media_objects += page.get("Count", 0)

        # Calculate reuse rate
        average_reuse_rate = (
            total_usage / total_search_terms if total_search_terms > 0 else 0
        )

        return {
            "total_media_objects": total_media_objects,
            "total_search_terms": total_search_terms,
            "total_usage": total_usage,
            "average_reuse_rate": round(average_reuse_rate, 2),
            "top_search_terms": search_term_stats[:10],  # Top 10
            "reuse_efficiency": round(
                (
                    total_media_objects / total_search_terms
                    if total_search_terms > 0
                    else 0
                ),
                2,
            ),
            "table_name": media_table.name,
        }

    except Exception as exc:
        logger.exception("media_stats_calculation_failed", error=str(exc))
        return {"error": str(exc)}


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
