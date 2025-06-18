import json
import os
from datetime import datetime, timedelta, timezone
from typing import Any, Dict

import boto3
from aws_lambda_powertools import Logger
from aws_lambda_powertools.utilities.typing import LambdaContext
from botocore.exceptions import ClientError

logger = Logger(service="vocab-processor-websocket")

# DynamoDB and WebSocket API setup
dynamodb = boto3.resource("dynamodb")
connections_table_name = os.environ.get("DYNAMODB_CONNECTIONS_TABLE_NAME")
vocab_table_name = os.environ.get("DYNAMODB_VOCAB_TABLE_NAME")

connections_table = (
    dynamodb.Table(connections_table_name) if connections_table_name else None
)
vocab_table = dynamodb.Table(vocab_table_name) if vocab_table_name else None


# API Gateway Management API setup
def get_api_gateway_management_api(event):
    """Create API Gateway Management API client from event context."""
    domain_name = event["requestContext"]["domainName"]
    stage = event["requestContext"]["stage"]
    endpoint_url = f"https://{domain_name}/{stage}"

    return boto3.client("apigatewaymanagementapi", endpoint_url=endpoint_url)


def lambda_response(status_code: int, body: str = "") -> Dict[str, Any]:
    """Create a properly formatted Lambda response for API Gateway."""
    return {"statusCode": status_code, "body": body}


def connect_handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """Handle WebSocket connection requests."""
    connection_id = event["requestContext"]["connectionId"]
    domain_name = event["requestContext"]["domainName"]
    stage = event["requestContext"]["stage"]

    # Extract user_id and optional vocab_word from query parameters
    query_params = event.get("queryStringParameters") or {}
    user_id = query_params.get("user_id", "anonymous")
    source_word = query_params.get("source_word")
    target_language = query_params.get("target_language")

    logger.info(
        "websocket_connection_request",
        connection_id=connection_id,
        user_id=user_id,
        source_word=source_word,
        target_language=target_language,
    )

    try:
        # Store connection in DynamoDB with TTL (30 minutes)
        ttl = int((datetime.now(timezone.utc) + timedelta(minutes=30)).timestamp())

        connection_item = {
            "connection_id": connection_id,
            "user_id": user_id,
            "connected_at": datetime.now(timezone.utc).isoformat(),
            "ttl": ttl,
            "websocket_endpoint": f"https://{domain_name}/{stage}",
        }

        # If word pair is provided, subscribe to it immediately
        if source_word and target_language:
            from vocab_processor.utils.websocket_utils import create_vocab_word_key

            vocab_word_key = create_vocab_word_key(source_word, target_language)
            connection_item["vocab_word"] = vocab_word_key
            connection_item["last_subscription"] = datetime.now(
                timezone.utc
            ).isoformat()

            logger.info(
                "immediate_vocab_word_subscription",
                connection_id=connection_id,
                vocab_word=vocab_word_key,
            )

        connections_table.put_item(Item=connection_item)

        logger.info(
            "websocket_connection_stored", connection_id=connection_id, user_id=user_id
        )

        return {"statusCode": 200}

    except Exception as e:
        logger.error(
            "websocket_connection_failed", connection_id=connection_id, error=str(e)
        )
        return {"statusCode": 500}


def disconnect_handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """Handle WebSocket disconnection requests."""
    connection_id = event["requestContext"]["connectionId"]

    logger.info("websocket_disconnection_request", connection_id=connection_id)

    try:
        # Remove connection from DynamoDB
        connections_table.delete_item(Key={"connection_id": connection_id})

        logger.info("websocket_connection_removed", connection_id=connection_id)

        return {"statusCode": 200}

    except Exception as e:
        logger.error(
            "websocket_disconnection_failed", connection_id=connection_id, error=str(e)
        )
        return {"statusCode": 500}


def default_handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """Handle default WebSocket messages (subscriptions, unsubscriptions, etc.)."""
    connection_id = event["requestContext"]["connectionId"]

    try:
        # Parse the message body
        body = json.loads(event.get("body", "{}"))
        action = body.get("action")

        logger.info(
            "websocket_message_received", connection_id=connection_id, action=action
        )

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


def handle_subscribe(connection_id: str, body: Dict[str, Any]) -> Dict[str, Any]:
    """Handle subscription to word pair updates."""
    source_word = body.get("source_word")
    target_language = body.get("target_language")

    if not source_word or not target_language:
        return {"statusCode": 400, "body": "Missing source_word or target_language"}

    try:
        from vocab_processor.utils.websocket_utils import create_vocab_word_key

        vocab_word_key = create_vocab_word_key(source_word, target_language)

        # Update the connection to subscribe to this word pair
        connections_table.update_item(
            Key={"connection_id": connection_id},
            UpdateExpression="SET vocab_word = :vocab_word, last_subscription = :timestamp",
            ExpressionAttributeValues={
                ":vocab_word": vocab_word_key,
                ":timestamp": datetime.now(timezone.utc).isoformat(),
            },
        )

        logger.info(
            "vocab_word_subscription_successful",
            connection_id=connection_id,
            vocab_word=vocab_word_key,
        )

        # Send confirmation message back to client
        api_gateway = boto3.client(
            "apigatewaymanagementapi",
            endpoint_url=f"https://{connections_table.get_item(Key={'connection_id': connection_id})['Item'].get('websocket_endpoint', '')}",
        )

        confirmation = {
            "type": "subscription_confirmed",
            "vocab_word": vocab_word_key,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

        api_gateway.post_to_connection(
            ConnectionId=connection_id, Data=json.dumps(confirmation)
        )

        return {"statusCode": 200}

    except Exception as e:
        logger.error(
            "vocab_word_subscription_failed", connection_id=connection_id, error=str(e)
        )
        return {"statusCode": 500}


def handle_unsubscribe(connection_id: str, body: Dict[str, Any]) -> Dict[str, Any]:
    """Handle unsubscription from word pair updates."""
    try:
        # Remove word pair subscription
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
        # Update the connection's last activity
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


def cleanup_stale_connections():
    """Clean up stale WebSocket connections (called periodically)."""
    if not connections_table:
        return

    try:
        # Scan for connections that are past their TTL
        current_time = int(datetime.now(timezone.utc).timestamp())

        response = connections_table.scan(
            FilterExpression="attribute_exists(ttl) AND ttl < :current_time",
            ExpressionAttributeValues={":current_time": current_time},
        )

        stale_connections = response.get("Items", [])

        for connection in stale_connections:
            connection_id = connection["connection_id"]
            try:
                connections_table.delete_item(Key={"connection_id": connection_id})
                logger.info("stale_connection_cleaned", connection_id=connection_id)
            except Exception as e:
                logger.error(
                    "stale_connection_cleanup_failed",
                    connection_id=connection_id,
                    error=str(e),
                )

        logger.info(
            "stale_connections_cleanup_completed", cleaned_count=len(stale_connections)
        )

    except Exception as e:
        logger.error("stale_connections_cleanup_error", error=str(e))


# AWS Lambda handler functions
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


def send_to_connection(
    connection_id: str, message: Dict[str, Any], api_gateway_client=None
) -> bool:
    """Send a message to a specific WebSocket connection."""
    try:
        if not api_gateway_client:
            # This requires the API Gateway endpoint, which we'll need to pass in
            # For now, we'll return False if no client is provided
            logger.warning("no_api_gateway_client", connection_id=connection_id)
            return False

        api_gateway_client.post_to_connection(
            ConnectionId=connection_id, Data=json.dumps(message)
        )

        logger.debug(
            "message_sent",
            connection_id=connection_id,
            message_type=message.get("type"),
        )
        return True

    except ClientError as e:
        if e.response["Error"]["Code"] == "GoneException":
            # Connection is stale, remove it from DynamoDB
            logger.info("stale_connection_cleanup", connection_id=connection_id)
            try:
                connections_table.delete_item(Key={"connection_id": connection_id})
            except Exception:
                pass
        else:
            logger.error(
                "send_message_failed", connection_id=connection_id, error=str(e)
            )

        return False


def broadcast_to_user_connections(
    user_id: str, message: Dict[str, Any], api_gateway_endpoint: str
) -> int:
    """Broadcast a message to all connections for a specific user."""
    try:
        # Create API Gateway client with the provided endpoint
        api_gateway = boto3.client(
            "apigatewaymanagementapi", endpoint_url=api_gateway_endpoint
        )

        # Query user connections
        response = connections_table.query(
            IndexName="UserConnectionsIndex",
            KeyConditionExpression="user_id = :user_id",
            ExpressionAttributeValues={":user_id": user_id},
        )

        connections = response.get("Items", [])
        successful_sends = 0

        for connection in connections:
            connection_id = connection["connection_id"]
            if send_to_connection(connection_id, message, api_gateway):
                successful_sends += 1

        logger.info(
            "user_broadcast_complete",
            user_id=user_id,
            total_connections=len(connections),
            successful_sends=successful_sends,
        )

        return successful_sends

    except Exception as e:
        logger.error("broadcast_failed", user_id=user_id, error=str(e))
        return 0


def broadcast_to_all_connections(
    message: Dict[str, Any], api_gateway_endpoint: str
) -> int:
    """Broadcast a message to all active connections."""
    try:
        # Create API Gateway client
        api_gateway = boto3.client(
            "apigatewaymanagementapi", endpoint_url=api_gateway_endpoint
        )

        # Scan all connections
        response = connections_table.scan()
        connections = response.get("Items", [])

        successful_sends = 0

        for connection in connections:
            connection_id = connection["connection_id"]
            if send_to_connection(connection_id, message, api_gateway):
                successful_sends += 1

        logger.info(
            "global_broadcast_complete",
            total_connections=len(connections),
            successful_sends=successful_sends,
        )

        return successful_sends

    except Exception as e:
        logger.error("global_broadcast_failed", error=str(e))
        return 0
