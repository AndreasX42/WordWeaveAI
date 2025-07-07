import json
import os
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, Optional, Tuple

import boto3
from aws_lambda_powertools import Logger
from botocore.exceptions import ClientError

logger = Logger(service="vocab-processor-websocket")

# DynamoDB setup
dynamodb = boto3.resource("dynamodb")
connections_table_name = os.getenv("DYNAMODB_CONNECTIONS_TABLE_NAME")
connections_table = (
    dynamodb.Table(connections_table_name) if connections_table_name else None
)


# =============================================================================
# UTILITY FUNCTIONS
# =============================================================================


def create_vocab_word_key(source_word: str, target_language: str) -> str:
    """Create a consistent key for vocab_word subscriptions."""
    import re
    import unicodedata

    def normalize_word(word: str) -> str:
        """Return lower‑case, accent‑stripped, alnum‑only version of word."""
        word = unicodedata.normalize("NFKC", word.lower())
        word = "".join(
            ch
            for ch in unicodedata.normalize("NFD", word)
            if unicodedata.category(ch) != "Mn"
        )
        return re.sub(r"[^a-z0-9]", "", word)

    return f"{target_language.lower()}#{normalize_word(source_word)}"


def get_connection_params(
    event: Dict[str, Any],
) -> Tuple[str, str, Optional[str], Optional[str]]:
    """Extract connection parameters from WebSocket event."""
    connection_id = event["requestContext"]["connectionId"]
    query_params = event.get("queryStringParameters") or {}
    user_id = query_params.get("user_id", "anonymous")
    source_word = query_params.get("source_word")
    target_language = query_params.get("target_language")
    return connection_id, user_id, source_word, target_language


def parse_websocket_message(event: Dict[str, Any]) -> Tuple[str, Dict[str, Any]]:
    """Parse WebSocket message and return connection_id and body."""
    connection_id = event["requestContext"]["connectionId"]
    body = json.loads(event.get("body", "{}"))
    return connection_id, body


def create_connection_item(
    connection_id: str,
    user_id: str,
    websocket_endpoint: str,
    source_word: Optional[str] = None,
    target_language: Optional[str] = None,
) -> Dict[str, Any]:
    """Create a connection item for DynamoDB storage."""
    ttl = int((datetime.now(timezone.utc) + timedelta(minutes=30)).timestamp())

    item = {
        "connection_id": connection_id,
        "user_id": user_id,
        "connected_at": datetime.now(timezone.utc).isoformat(),
        "ttl": ttl,
        "websocket_endpoint": websocket_endpoint,
    }

    if source_word and target_language:
        vocab_word_key = create_vocab_word_key(source_word, target_language)
        item["vocab_word"] = vocab_word_key
        item["last_subscription"] = datetime.now(timezone.utc).isoformat()

    return item


# =============================================================================
# CORE DATABASE FUNCTIONS
# =============================================================================


def store_connection(connection_item: Dict[str, Any]) -> bool:
    """Store connection in DynamoDB."""
    try:
        connections_table.put_item(Item=connection_item)
        return True
    except Exception as e:
        logger.error("store_connection_failed", error=str(e))
        return False


def remove_connection(connection_id: str) -> bool:
    """Remove connection from DynamoDB."""
    try:
        connections_table.delete_item(Key={"connection_id": connection_id})
        return True
    except Exception as e:
        logger.error(
            "remove_connection_failed", connection_id=connection_id, error=str(e)
        )
        return False


def update_connection_subscription(connection_id: str, vocab_word_key: str) -> bool:
    """Update connection subscription in DynamoDB."""
    try:
        connections_table.update_item(
            Key={"connection_id": connection_id},
            UpdateExpression="SET vocab_word = :vocab_word, last_subscription = :timestamp",
            ExpressionAttributeValues={
                ":vocab_word": vocab_word_key,
                ":timestamp": datetime.now(timezone.utc).isoformat(),
            },
        )
        return True
    except Exception as e:
        logger.error(
            "update_subscription_failed", connection_id=connection_id, error=str(e)
        )
        return False


def cleanup_stale_connections():
    """Clean up stale WebSocket connections (called periodically)."""
    if not connections_table:
        return

    try:
        current_time = int(datetime.now(timezone.utc).timestamp())
        response = connections_table.scan(
            FilterExpression="attribute_exists(ttl) AND ttl < :current_time",
            ExpressionAttributeValues={":current_time": current_time},
        )

        stale_connections = response.get("Items", [])
        cleaned_count = 0

        for connection in stale_connections:
            connection_id = connection["connection_id"]
            if remove_connection(connection_id):
                cleaned_count += 1

        logger.info("stale_connections_cleanup_completed", cleaned_count=cleaned_count)

    except Exception as e:
        logger.error("stale_connections_cleanup_error", error=str(e))


# =============================================================================
# WEBSOCKET FUNCTIONS
# =============================================================================


def send_subscription_confirmation(
    connection_id: str, vocab_word_key: str, source_word: str, target_language: str
) -> None:
    """Send subscription confirmation to client."""
    try:
        connection_info = connections_table.get_item(
            Key={"connection_id": connection_id}
        )
        websocket_endpoint = connection_info.get("Item", {}).get(
            "websocket_endpoint", ""
        )

        if not websocket_endpoint:
            logger.warning("no_websocket_endpoint_found", connection_id=connection_id)
            return

        api_gateway = boto3.client(
            "apigatewaymanagementapi", endpoint_url=websocket_endpoint
        )

        confirmation = {
            "type": "subscription_confirmed",
            "vocab_word": vocab_word_key,
            "source_word": source_word,
            "target_language": target_language,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

        api_gateway.post_to_connection(
            ConnectionId=connection_id, Data=json.dumps(confirmation)
        )

        logger.info("subscription_confirmation_sent", connection_id=connection_id)

    except Exception as e:
        logger.error(
            "subscription_confirmation_failed",
            connection_id=connection_id,
            error=str(e),
        )


# =============================================================================
# MESSAGE HANDLERS
# =============================================================================


def handle_subscribe(connection_id: str, body: Dict[str, Any]) -> Dict[str, Any]:
    """Handle subscription to word pair updates."""
    source_word = body.get("source_word")
    target_language = body.get("target_language")

    logger.info(
        "subscription_request",
        connection_id=connection_id,
        source_word=source_word,
        target_language=target_language,
    )

    if not source_word or not target_language:
        logger.error("invalid_subscription_request", connection_id=connection_id)
        return {"statusCode": 400, "body": "Missing source_word or target_language"}

    vocab_word_key = create_vocab_word_key(source_word, target_language)

    if update_connection_subscription(connection_id, vocab_word_key):
        logger.info("vocab_word_subscription_successful", connection_id=connection_id)
        send_subscription_confirmation(
            connection_id, vocab_word_key, source_word, target_language
        )
        return {"statusCode": 200}
    else:
        return {"statusCode": 500}


def handle_unsubscribe(connection_id: str, body: Dict[str, Any]) -> Dict[str, Any]:
    """Handle unsubscription from word pair updates."""
    try:
        connections_table.update_item(
            Key={"connection_id": connection_id},
            UpdateExpression="REMOVE vocab_word, last_subscription",
        )
        logger.info("vocab_word_unsubscription_successful", connection_id=connection_id)
        return {"statusCode": 200}
    except Exception as e:
        logger.error(
            "vocab_word_unsubscription_failed",
            connection_id=connection_id,
            error=str(e),
        )
        return {"statusCode": 500}


def handle_ping(connection_id: str) -> Dict[str, Any]:
    """Handle ping messages to keep connection alive."""
    try:
        connections_table.update_item(
            Key={"connection_id": connection_id},
            UpdateExpression="SET last_ping = :timestamp",
            ExpressionAttributeValues={
                ":timestamp": datetime.now(timezone.utc).isoformat()
            },
        )
        return {"statusCode": 200}
    except Exception as e:
        logger.error("ping_failed", connection_id=connection_id, error=str(e))
        return {"statusCode": 500}


# =============================================================================
# WEBSOCKET EVENT HANDLERS
# =============================================================================


def connect_handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """Handle WebSocket connection requests."""
    connection_id, user_id, source_word, target_language = get_connection_params(event)

    domain_name = event["requestContext"]["domainName"]
    stage = event["requestContext"]["stage"]
    websocket_endpoint = f"https://{domain_name}/{stage}"

    logger.info(
        "websocket_connection_request",
        connection_id=connection_id,
        user_id=user_id,
        source_word=source_word,
        target_language=target_language,
    )

    connection_item = create_connection_item(
        connection_id, user_id, websocket_endpoint, source_word, target_language
    )

    if source_word and target_language:
        logger.info(
            "immediate_vocab_word_subscription",
            connection_id=connection_id,
            vocab_word=connection_item["vocab_word"],
        )

    if store_connection(connection_item):
        logger.info("websocket_connection_stored", connection_id=connection_id)
        return {"statusCode": 200}
    else:
        return {"statusCode": 500}


def disconnect_handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """Handle WebSocket disconnection requests."""
    connection_id = event["requestContext"]["connectionId"]
    logger.info("websocket_disconnection_request", connection_id=connection_id)

    if remove_connection(connection_id):
        logger.info("websocket_connection_removed", connection_id=connection_id)
        return {"statusCode": 200}
    else:
        return {"statusCode": 500}


def default_handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """Handle default WebSocket messages (subscriptions, unsubscriptions, etc.)."""
    connection_id, body = parse_websocket_message(event)
    action = body.get("action")

    logger.info(
        "websocket_message_received",
        connection_id=connection_id,
        action=action,
    )

    try:
        if action == "subscribe":
            return handle_subscribe(connection_id, body)
        elif action == "unsubscribe":
            return handle_unsubscribe(connection_id, body)
        elif action == "ping":
            return handle_ping(connection_id)
        else:
            logger.warning(
                "unknown_websocket_action", connection_id=connection_id, action=action
            )
            return {"statusCode": 400}
    except Exception as e:
        logger.error(
            "websocket_message_failed", connection_id=connection_id, error=str(e)
        )
        return {"statusCode": 500}


# =============================================================================
# MAIN LAMBDA HANDLER
# =============================================================================


def lambda_handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """Main Lambda handler for WebSocket API Gateway events."""
    route_key = event["requestContext"]["routeKey"]

    if route_key == "$connect":
        return connect_handler(event, context)
    elif route_key == "$disconnect":
        return disconnect_handler(event, context)
    elif route_key == "$default":
        return default_handler(event, context)
    else:
        logger.warning("unknown_route_key", route_key=route_key)
        return {"statusCode": 400}
