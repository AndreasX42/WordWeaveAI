import json
import os
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

import boto3
from aws_lambda_powertools import Logger
from botocore.exceptions import ClientError

logger = Logger(service="vocab-processor-websocket")

# DynamoDB and API Gateway setup
dynamodb = boto3.resource("dynamodb")
connections_table_name = os.environ.get("DYNAMODB_CONNECTIONS_TABLE_NAME")
websocket_api_endpoint = os.environ.get("WEBSOCKET_API_ENDPOINT")

# Cache the connections table and API Gateway client
_connections_table = None
_api_gateway_client = None


def get_connections_table():
    """Get DynamoDB connections table (cached)."""
    global _connections_table
    if _connections_table is None and connections_table_name:
        _connections_table = dynamodb.Table(connections_table_name)
    return _connections_table


def get_api_gateway_client():
    """Get API Gateway Management API client (cached)."""
    global _api_gateway_client
    if _api_gateway_client is None and websocket_api_endpoint:
        _api_gateway_client = boto3.client(
            "apigatewaymanagementapi", endpoint_url=websocket_api_endpoint
        )
    return _api_gateway_client


def create_vocab_word_key(source_word: str, target_language: str) -> str:
    """Create a consistent key for vocab_word subscriptions."""
    from vocab_processor.utils.ddb_utils import normalize_word

    return f"{target_language.lower()}#{normalize_word(source_word)}"


class WebSocketNotifier:
    """Handle WebSocket notifications for vocab processing updates with multi-user support."""

    def __init__(self, user_id: Optional[str] = None, request_id: Optional[str] = None):
        self.user_id = user_id or "anonymous"
        self.request_id = request_id
        self.connections_table = get_connections_table()
        self.api_gateway = get_api_gateway_client()

    def _create_message(
        self, message_type: str, data: Any, step: Optional[str] = None
    ) -> Dict[str, Any]:
        """Create a standardized WebSocket message."""
        message = {
            "type": message_type,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "user_id": self.user_id,
            "data": data,
        }

        if self.request_id:
            message["request_id"] = self.request_id

        if step:
            message["step"] = step

        return message

    def _send_to_connection(self, connection_id: str, message: Dict[str, Any]) -> bool:
        """Send a message to a specific WebSocket connection."""
        if not self.api_gateway:
            logger.debug("websocket_not_configured")
            return False

        try:
            self.api_gateway.post_to_connection(
                ConnectionId=connection_id, Data=json.dumps(message)
            )
            return True

        except ClientError as e:
            if e.response["Error"]["Code"] == "GoneException":
                # Connection is stale, remove it
                logger.info("stale_connection_removed", connection_id=connection_id)
                if self.connections_table:
                    try:
                        self.connections_table.delete_item(
                            Key={"connection_id": connection_id}
                        )
                    except Exception:
                        pass
            else:
                logger.error(
                    "websocket_send_failed", connection_id=connection_id, error=str(e)
                )
            return False

    def _get_vocab_word_subscribers(
        self, source_word: str, target_language: str
    ) -> List[Dict]:
        """Get all connections subscribed to a specific vocab_word."""
        if not self.connections_table:
            return []

        vocab_word_key = create_vocab_word_key(source_word, target_language)

        try:
            # Use GSI to find all connections subscribed to this word pair
            response = self.connections_table.query(
                IndexName="VocabWordConnectionsIndex",
                KeyConditionExpression="vocab_word = :vocab_word",
                ExpressionAttributeValues={":vocab_word": vocab_word_key},
            )
            return response.get("Items", [])
        except Exception as e:
            logger.error(
                "get_vocab_word_subscribers_failed",
                vocab_word=vocab_word_key,
                error=str(e),
            )
            return []

    def _get_user_connections(self) -> List[Dict]:
        """Get all active connections for the current user."""
        if not self.connections_table:
            return []

        try:
            response = self.connections_table.query(
                IndexName="UserConnectionsIndex",
                KeyConditionExpression="user_id = :user_id",
                ExpressionAttributeValues={":user_id": self.user_id},
            )
            return response.get("Items", [])
        except Exception as e:
            logger.error("get_connections_failed", user_id=self.user_id, error=str(e))
            return []

    def subscribe_to_vocab_word(
        self, connection_id: str, source_word: str, target_language: str
    ):
        """Subscribe a connection to vocab_word updates."""
        if not self.connections_table:
            return False

        vocab_word_key = create_vocab_word_key(source_word, target_language)

        try:
            # Update the connection to include the vocab_word subscription
            self.connections_table.update_item(
                Key={"connection_id": connection_id},
                UpdateExpression="SET vocab_word = :vocab_word, last_subscription = :timestamp",
                ExpressionAttributeValues={
                    ":vocab_word": vocab_word_key,
                    ":timestamp": datetime.now(timezone.utc).isoformat(),
                },
            )

            logger.info(
                "vocab_word_subscription_added",
                connection_id=connection_id,
                vocab_word=vocab_word_key,
            )
            return True

        except Exception as e:
            logger.error(
                "vocab_word_subscription_failed",
                connection_id=connection_id,
                vocab_word=vocab_word_key,
                error=str(e),
            )
            return False

    def send_processing_started(self, source_word: str, target_language: str):
        """Notify ALL subscribers that vocab processing has started for this word pair."""
        message = self._create_message(
            "processing_started",
            {
                "source_word": source_word,
                "target_language": target_language,
                "status": "started",
            },
        )
        self._broadcast_to_vocab_word_subscribers(source_word, target_language, message)

    def send_step_update(
        self,
        source_word: str,
        target_language: str,
        step_name: str,
        step_data: Any,
        status: str = "running",
    ):
        """Send an update for a specific processing step to ALL subscribers."""
        message = self._create_message(
            "step_update",
            {
                "source_word": source_word,
                "target_language": target_language,
                "status": status,
                "result": step_data,
            },
            step=step_name,
        )
        self._broadcast_to_vocab_word_subscribers(source_word, target_language, message)

    def send_chunk_update(
        self, source_word: str, target_language: str, chunk_data: Any
    ):
        """Send a real-time chunk update from LangGraph streaming to ALL subscribers."""
        message = self._create_message(
            "chunk_update",
            {
                "source_word": source_word,
                "target_language": target_language,
                "chunk": chunk_data,
            },
        )
        self._broadcast_to_vocab_word_subscribers(source_word, target_language, message)

    def send_processing_completed(
        self, source_word: str, target_language: str, result: Dict[str, Any]
    ):
        """Notify ALL subscribers that vocab processing has completed for this word pair."""
        message = self._create_message(
            "processing_completed",
            {
                "source_word": source_word,
                "target_language": target_language,
                "status": "completed",
                "result": result,
            },
        )
        self._broadcast_to_vocab_word_subscribers(source_word, target_language, message)

    def send_processing_failed(
        self, source_word: str, target_language: str, error: str
    ):
        """Notify ALL subscribers that vocab processing has failed for this word pair."""
        message = self._create_message(
            "processing_failed",
            {
                "source_word": source_word,
                "target_language": target_language,
                "status": "failed",
                "error": error,
            },
        )
        self._broadcast_to_vocab_word_subscribers(source_word, target_language, message)

    def send_cache_hit(
        self, source_word: str, target_language: str, cached_data: Dict[str, Any]
    ):
        """Notify ALL subscribers that a cache hit occurred for this word pair."""
        message = self._create_message(
            "cache_hit",
            {
                "source_word": source_word,
                "target_language": target_language,
                "status": "cached",
                "result": cached_data,
            },
        )
        self._broadcast_to_vocab_word_subscribers(source_word, target_language, message)

    def _broadcast_to_vocab_word_subscribers(
        self, source_word: str, target_language: str, message: Dict[str, Any]
    ) -> int:
        """Broadcast a message to ALL connections subscribed to this word pair."""
        connections = self._get_vocab_word_subscribers(source_word, target_language)
        successful_sends = 0

        for connection in connections:
            connection_id = connection["connection_id"]
            if self._send_to_connection(connection_id, message):
                successful_sends += 1

        vocab_word_key = create_vocab_word_key(source_word, target_language)
        logger.info(
            "vocab_word_broadcast",
            vocab_word=vocab_word_key,
            message_type=message.get("type"),
            total_subscribers=len(connections),
            successful_sends=successful_sends,
            initiated_by=self.user_id,
        )

        return successful_sends

    def _broadcast_to_user(self, message: Dict[str, Any]) -> int:
        """Broadcast a message to all user connections (legacy method for user-specific messages)."""
        connections = self._get_user_connections()
        successful_sends = 0

        for connection in connections:
            connection_id = connection["connection_id"]
            if self._send_to_connection(connection_id, message):
                successful_sends += 1

        logger.debug(
            "user_broadcast",
            user_id=self.user_id,
            message_type=message.get("type"),
            total_connections=len(connections),
            successful_sends=successful_sends,
        )

        return successful_sends


# Enhanced convenience functions for multi-user notifications
def notify_processing_started(
    source_word: str, target_language: str, user_id: str = None, request_id: str = None
):
    """Quick function to notify ALL subscribers that processing started."""
    notifier = WebSocketNotifier(user_id, request_id)
    notifier.send_processing_started(source_word, target_language)


def notify_chunk_update(
    source_word: str,
    target_language: str,
    chunk_data: Any,
    user_id: str = None,
    request_id: str = None,
):
    """Quick function to send chunk updates to ALL subscribers."""
    notifier = WebSocketNotifier(user_id, request_id)
    notifier.send_chunk_update(source_word, target_language, chunk_data)


def notify_processing_completed(
    source_word: str,
    target_language: str,
    result: Dict[str, Any],
    user_id: str = None,
    request_id: str = None,
):
    """Quick function to notify ALL subscribers that processing completed."""
    notifier = WebSocketNotifier(user_id, request_id)
    notifier.send_processing_completed(source_word, target_language, result)


def notify_processing_failed(
    source_word: str,
    target_language: str,
    error: str,
    user_id: str = None,
    request_id: str = None,
):
    """Quick function to notify ALL subscribers that processing failed."""
    notifier = WebSocketNotifier(user_id, request_id)
    notifier.send_processing_failed(source_word, target_language, error)


def subscribe_connection_to_vocab_word(
    connection_id: str, source_word: str, target_language: str, user_id: str = None
):
    """Subscribe a WebSocket connection to receive updates for a specific vocab_word."""
    notifier = WebSocketNotifier(user_id)
    return notifier.subscribe_to_vocab_word(connection_id, source_word, target_language)
