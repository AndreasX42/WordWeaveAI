import asyncio
import json
import logging
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Optional
from unittest.mock import MagicMock, patch

from rich.console import Console
from rich.panel import Panel
from rich.table import Table

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Import test setup to initialize AWS mocks before any other imports
from test_setup import get_mock_services

# Now import the application modules
from handlers.vocab_handler import _handle_request
from handlers.websocket_handler import (
    connect_handler,
    default_handler,
    disconnect_handler,
)
from vocab_processor.constants import Language
from vocab_processor.utils.ddb_utils import VocabProcessRequestDto

console = Console()


@dataclass
class MockWebSocketConnection:
    """Mock WebSocket connection for testing."""

    connection_id: str
    user_id: str
    source_word: Optional[str] = None
    target_language: Optional[str] = None
    messages_received: list[dict[str, Any]] = field(default_factory=list)
    is_connected: bool = True

    def receive_message(self, message: dict[str, Any]):
        """Simulate receiving a message."""
        self.messages_received.append(message)

    def disconnect(self):
        """Simulate disconnection."""
        self.is_connected = False


@dataclass
class LambdaTestResult:
    """Result of a lambda test execution."""

    request: VocabProcessRequestDto
    response: dict[str, Any]
    execution_time: float
    error: Optional[str] = None
    websocket_notifications: list[dict[str, Any]] = field(default_factory=list)
    ddb_operations: list[dict[str, Any]] = field(default_factory=list)


@dataclass
class WebSocketTestResult:
    """Result of a websocket test execution."""

    connection_id: str
    action: str
    response: dict[str, Any]
    error: Optional[str] = None
    messages_sent: list[dict[str, Any]] = field(default_factory=list)


class MockDynamoDBTable:
    """Mock DynamoDB table for testing."""

    def __init__(self):
        self.items = {}
        self.operations = []

    def put_item(self, **kwargs):
        """Mock put_item operation."""
        item = kwargs.get("Item", {})
        key = item.get("PK", "") + "#" + item.get("SK", "")
        self.items[key] = item
        self.operations.append({"operation": "put_item", "item": item})
        return {"ResponseMetadata": {"HTTPStatusCode": 200}}

    def get_item(self, **kwargs):
        """Mock get_item operation."""
        key_dict = kwargs.get("Key", {})
        key = key_dict.get("PK", "") + "#" + key_dict.get("SK", "")
        item = self.items.get(key)
        self.operations.append(
            {"operation": "get_item", "key": key_dict, "found": item is not None}
        )
        return {"Item": item} if item else {}

    def query(self, **kwargs):
        """Mock query operation."""
        # Simple mock - return items based on key condition
        key_condition = kwargs.get("KeyConditionExpression", "")
        index_name = kwargs.get("IndexName", "")
        expression_values = kwargs.get("ExpressionAttributeValues", {})

        # Handle vocab word connection queries
        if (
            index_name == "VocabWordConnectionsIndex"
            and ":vocab_word" in expression_values
        ):
            vocab_word = expression_values[":vocab_word"]
            matching_items = [
                item
                for item in self.items.values()
                if item.get("vocab_word") == vocab_word
            ]
            self.operations.append(
                {
                    "operation": "query",
                    "condition": key_condition,
                    "count": len(matching_items),
                }
            )
            return {"Items": matching_items}

        # Handle user connection queries
        elif index_name == "UserConnectionsIndex" and ":user_id" in expression_values:
            user_id = expression_values[":user_id"]
            matching_items = [
                item for item in self.items.values() if item.get("user_id") == user_id
            ]
            self.operations.append(
                {
                    "operation": "query",
                    "condition": key_condition,
                    "count": len(matching_items),
                }
            )
            return {"Items": matching_items}

        # Default behavior
        items = list(self.items.values())
        self.operations.append(
            {"operation": "query", "condition": key_condition, "count": len(items)}
        )
        return {"Items": items}

    def update_item(self, **kwargs):
        """Mock update_item operation."""
        key_dict = kwargs.get("Key", {})
        key = key_dict.get("PK", "") + "#" + key_dict.get("SK", "")
        update_expr = kwargs.get("UpdateExpression", "")
        self.operations.append(
            {"operation": "update_item", "key": key_dict, "update": update_expr}
        )
        return {"ResponseMetadata": {"HTTPStatusCode": 200}}

    def delete_item(self, **kwargs):
        """Mock delete_item operation."""
        key_dict = kwargs.get("Key", {})
        key = key_dict.get("PK", "") + "#" + key_dict.get("SK", "")
        if key in self.items:
            del self.items[key]
        self.operations.append({"operation": "delete_item", "key": key_dict})
        return {"ResponseMetadata": {"HTTPStatusCode": 200}}


class IntegrationTestFramework:
    """Integration test framework for Lambda and WebSocket functionality."""

    def __init__(self):
        self.mock_connections = {}
        self.mock_vocab_table = MockDynamoDBTable()
        self.mock_connections_table = MockDynamoDBTable()
        self.mock_media_table = MockDynamoDBTable()

        # Use the global mock API Gateway from test_setup
        mock_services = get_mock_services()
        self.mock_api_gateway = mock_services["api_gateway"]

        # Setup mock responses for existing words
        self._setup_existing_words()

    def _setup_existing_words(self):
        """Setup some existing words in the mock database for testing."""
        existing_words = [
            {
                "PK": "WORD#spanish#hola",
                "SK": "LANG#english",
                "source_word": "hola",
                "source_language": "spanish",
                "target_word": "hello",
                "target_language": "english",
                "source_pos": "interjection",
                "target_pos": "interjection",
                "source_definition": ["A greeting used when meeting someone"],
                "created_at": "2024-01-01T00:00:00Z",
            },
            {
                "PK": "WORD#german#haus",
                "SK": "LANG#english",
                "source_word": "haus",
                "source_language": "german",
                "target_word": "house",
                "target_language": "english",
                "source_pos": "noun",
                "target_pos": "noun",
                "source_article": "das",
                "target_article": "the",
                "source_definition": ["A building for human habitation"],
                "created_at": "2024-01-01T00:00:00Z",
            },
        ]

        for word in existing_words:
            key = word["PK"] + "#" + word["SK"]
            self.mock_vocab_table.items[key] = word

    def _setup_mock_connections_for_vocab_word(
        self, source_word: str, target_language: str
    ):
        """Set up mock WebSocket connections for a specific vocab word to receive notifications."""
        from vocab_processor.utils.websocket_utils import create_vocab_word_key

        vocab_word_key = create_vocab_word_key(source_word, target_language)

        # Create mock connections subscribed to this vocab word
        mock_connections = [
            {
                "connection_id": "test_conn_lambda_1",
                "user_id": "test_user",
                "vocab_word": vocab_word_key,
                "connected_at": "2024-01-01T00:00:00Z",
                "ttl": 9999999999,  # Far future TTL
            },
            {
                "connection_id": "test_conn_lambda_2",
                "user_id": "test_user",
                "vocab_word": vocab_word_key,
                "connected_at": "2024-01-01T00:00:00Z",
                "ttl": 9999999999,  # Far future TTL
            },
        ]

        # Store connections in mock DynamoDB table
        for connection in mock_connections:
            self.mock_connections_table.put_item(Item=connection)

    def create_mock_connection(
        self, user_id: str, source_word: str = None, target_language: str = None
    ) -> MockWebSocketConnection:
        """Create a mock WebSocket connection."""
        connection_id = f"mock_conn_{len(self.mock_connections)}"
        connection = MockWebSocketConnection(
            connection_id=connection_id,
            user_id=user_id,
            source_word=source_word,
            target_language=target_language,
        )
        self.mock_connections[connection_id] = connection
        return connection

    def create_vocab_request(
        self,
        source_word: str,
        target_language: str,
        source_language: str = None,
        user_id: str = "test_user",
    ) -> VocabProcessRequestDto:
        """Create a vocab processing request."""
        return VocabProcessRequestDto(
            source_word=source_word,
            target_language=target_language,
            source_language=source_language,
            user_id=user_id,
            request_id=f"test_req_{datetime.now().timestamp()}",
        )

    async def test_lambda_scenario(
        self, request: VocabProcessRequestDto, mock_graph_result: dict[str, Any] = None
    ) -> LambdaTestResult:
        """Test a lambda processing scenario."""
        start_time = asyncio.get_event_loop().time()

        # Clear any previous call history
        self.mock_api_gateway.reset_mock()

        # Ensure post_to_connection is properly set up for tracking
        if not hasattr(self.mock_api_gateway, "post_to_connection"):
            self.mock_api_gateway.post_to_connection = MagicMock(
                return_value={"StatusCode": 200}
            )

        # Set up mock connections for WebSocket notifications
        self._setup_mock_connections_for_vocab_word(
            request.source_word, request.target_language
        )

        # Mock the graph execution if provided
        if mock_graph_result:
            with patch("vocab_processor.agent.graph.astream") as mock_astream:

                async def mock_stream_generator():
                    yield mock_graph_result

                mock_astream.return_value = mock_stream_generator()

                # Mock DynamoDB tables and AWS clients
                with patch(
                    "vocab_processor.utils.ddb_utils.VOCAB_TABLE",
                    self.mock_vocab_table,
                ), patch(
                    "vocab_processor.utils.ddb_utils.MEDIA_TABLE",
                    self.mock_media_table,
                ), patch(
                    "vocab_processor.utils.ddb_utils.get_media_table",
                    return_value=self.mock_media_table,
                ), patch(
                    "vocab_processor.utils.websocket_utils.get_connections_table",
                    return_value=self.mock_connections_table,
                ), patch(
                    "vocab_processor.utils.websocket_utils.get_api_gateway_client",
                    return_value=self.mock_api_gateway,
                ), patch(
                    "handlers.websocket_handler.connections_table",
                    self.mock_connections_table,
                ), patch(
                    "vocab_processor.utils.core_utils.is_lambda_context",
                    return_value=True,
                ):

                    try:
                        response = await _handle_request(request)
                        execution_time = asyncio.get_event_loop().time() - start_time

                        return LambdaTestResult(
                            request=request,
                            response=response,
                            execution_time=execution_time,
                            websocket_notifications=self._extract_websocket_notifications(),
                            ddb_operations=self.mock_vocab_table.operations
                            + self.mock_connections_table.operations,
                        )
                    except Exception as e:
                        execution_time = asyncio.get_event_loop().time() - start_time
                        return LambdaTestResult(
                            request=request,
                            response={},
                            execution_time=execution_time,
                            error=str(e),
                            websocket_notifications=self._extract_websocket_notifications(),
                            ddb_operations=self.mock_vocab_table.operations
                            + self.mock_connections_table.operations,
                        )
        else:
            # Run with real graph but mock dependencies
            with patch(
                "vocab_processor.utils.ddb_utils.VOCAB_TABLE",
                self.mock_vocab_table,
            ), patch(
                "vocab_processor.utils.ddb_utils.MEDIA_TABLE",
                self.mock_media_table,
            ), patch(
                "vocab_processor.utils.ddb_utils.get_media_table",
                return_value=self.mock_media_table,
            ), patch(
                "vocab_processor.utils.websocket_utils.get_connections_table",
                return_value=self.mock_connections_table,
            ), patch(
                "vocab_processor.utils.websocket_utils.get_api_gateway_client",
                return_value=self.mock_api_gateway,
            ), patch(
                "handlers.websocket_handler.connections_table",
                self.mock_connections_table,
            ), patch(
                "vocab_processor.utils.core_utils.is_lambda_context",
                return_value=True,
            ):

                try:
                    response = await _handle_request(request)
                    execution_time = asyncio.get_event_loop().time() - start_time

                    return LambdaTestResult(
                        request=request,
                        response=response,
                        execution_time=execution_time,
                        websocket_notifications=self._extract_websocket_notifications(),
                        ddb_operations=self.mock_vocab_table.operations
                        + self.mock_connections_table.operations,
                    )
                except Exception as e:
                    execution_time = asyncio.get_event_loop().time() - start_time
                    return LambdaTestResult(
                        request=request,
                        response={},
                        execution_time=execution_time,
                        error=str(e),
                        websocket_notifications=self._extract_websocket_notifications(),
                        ddb_operations=self.mock_vocab_table.operations
                        + self.mock_connections_table.operations,
                    )

    def test_websocket_scenario(
        self, event: dict[str, Any], context: Any = None
    ) -> WebSocketTestResult:
        """Test a websocket scenario."""

        # Reset API Gateway mock before each test
        self.mock_api_gateway.reset_mock()

        # Ensure post_to_connection is properly set up for tracking
        if not hasattr(self.mock_api_gateway, "post_to_connection"):
            self.mock_api_gateway.post_to_connection = MagicMock(
                return_value={"StatusCode": 200}
            )

        with patch(
            "handlers.websocket_handler.connections_table", self.mock_connections_table
        ), patch(
            "vocab_processor.utils.websocket_utils.get_api_gateway_client",
            return_value=self.mock_api_gateway,
        ):
            try:
                route_key = event["requestContext"]["routeKey"]

                if route_key == "$connect":
                    response = connect_handler(event, context)
                elif route_key == "$disconnect":
                    response = disconnect_handler(event, context)
                elif route_key == "$default":
                    response = default_handler(event, context)
                else:
                    response = {"statusCode": 400, "body": "Unknown route"}

                connection_id = event["requestContext"]["connectionId"]

                # Parse body if it's a JSON string
                body = event.get("body", "{}")
                if isinstance(body, str):
                    try:
                        body = json.loads(body)
                    except (json.JSONDecodeError, TypeError):
                        body = {}

                action = body.get("action", route_key)

                return WebSocketTestResult(
                    connection_id=connection_id,
                    action=action,
                    response=response,
                    messages_sent=self._extract_websocket_notifications(),
                )
            except Exception as e:
                # Parse body safely for error handling
                body = event.get("body", "{}")
                if isinstance(body, str):
                    try:
                        body = json.loads(body)
                    except (json.JSONDecodeError, TypeError):
                        body = {}

                return WebSocketTestResult(
                    connection_id=event["requestContext"]["connectionId"],
                    action=body.get("action", "unknown"),
                    response={"statusCode": 500},
                    error=str(e),
                )

    def _extract_websocket_notifications(self) -> list[dict[str, Any]]:
        """Extract WebSocket notifications from mock API Gateway calls."""
        notifications = []
        if (
            hasattr(self.mock_api_gateway, "post_to_connection")
            and self.mock_api_gateway.post_to_connection.call_args_list
        ):
            for call in self.mock_api_gateway.post_to_connection.call_args_list:
                args, kwargs = call
                try:
                    data = kwargs.get("Data", "{}")
                    if isinstance(data, str):
                        data = json.loads(data)

                    notifications.append(
                        {
                            "connection_id": kwargs.get("ConnectionId"),
                            "data": data,
                        }
                    )
                except (json.JSONDecodeError, TypeError) as e:
                    logger.warning(f"Failed to parse notification data: {e}")

        return notifications

    def assert_notification_sent(
        self,
        notifications: list[dict[str, Any]],
        message_type: str,
        expected_data: dict[str, Any] = None,
    ):
        """Assert that a specific notification was sent."""
        found = False
        for notification in notifications:
            data = notification.get("data", {})
            if data.get("type") == message_type:
                if expected_data:
                    for key, value in expected_data.items():
                        if key not in data.get("data", {}):
                            continue
                        if data["data"][key] != value:
                            continue
                found = True
                break

        assert (
            found
        ), f"Expected notification of type '{message_type}' not found in {notifications}"

    def print_test_results(self, results: list[LambdaTestResult]):
        """Print formatted test results."""
        console.print(
            Panel("LAMBDA & WEBSOCKET INTEGRATION TEST RESULTS", style="cyan bold")
        )

        table = Table()
        table.add_column("Test Case", style="cyan")
        table.add_column("Status", style="bold")
        table.add_column("Execution Time", style="yellow")
        table.add_column("WebSocket Notifications", style="blue")
        table.add_column("DDB Operations", style="green")

        for result in results:
            status = (
                "[green]✓ PASS[/green]" if not result.error else "[red]✗ FAIL[/red]"
            )
            exec_time = f"{result.execution_time:.2f}s"
            ws_count = len(result.websocket_notifications)
            ddb_count = len(result.ddb_operations)

            table.add_row(
                f"{result.request.source_word} -> {result.request.target_language}",
                status,
                exec_time,
                str(ws_count),
                str(ddb_count),
            )

        console.print(table)

        # Print detailed results for failures
        for result in results:
            if result.error:
                console.print(
                    f"\n[red]FAILED: {result.request.source_word} -> {result.request.target_language}[/red]"
                )
                console.print(f"Error: {result.error}")
                console.print(
                    f"WebSocket Notifications: {result.websocket_notifications}"
                )


# Test case definitions for different scenarios
class TestScenarios:
    """Predefined test scenarios for different edge cases."""

    @staticmethod
    def new_vocab_request():
        """Scenario 1: New vocab request - complete processing."""
        return {
            "request": VocabProcessRequestDto(
                source_word="beautiful",
                target_language="es",
                source_language="en",
                user_id="test_user",
                request_id="test_new_vocab",
            ),
            "expected_response_fields": [
                "source_word",
                "target_word",
                "processing_complete",
            ],
            "expected_notifications": ["processing_started", "processing_completed"],
            "expected_ddb_operations": ["put_item"],  # Should store result
        }

    @staticmethod
    def existing_word_request():
        """Scenario 2: Word already exists - DDB hit."""
        return {
            "request": VocabProcessRequestDto(
                source_word="hola",
                target_language="en",
                source_language="es",
                user_id="test_user",
                request_id="test_existing_word",
            ),
            "mock_graph_result": {
                "source_word": "hola",
                "target_language": Language.ENGLISH,
                "source_language": Language.SPANISH,
                "word_exists": True,
                "existing_item": {
                    "source_word": "hola",
                    "target_word": "hello",
                    "source_pos": "interjection",
                },
            },
            "expected_response_fields": ["status", "source_word", "ddb_hit"],
            "expected_notifications": ["processing_started", "ddb_hit"],
            "expected_ddb_operations": [],  # Should not store new result
        }

    @staticmethod
    def invalid_word_request():
        """Scenario 3: Invalid word - validation fails."""
        return {
            "request": VocabProcessRequestDto(
                source_word="xyz123invalid",
                target_language="es",
                source_language="en",
                user_id="test_user",
                request_id="test_invalid_word",
            ),
            "mock_graph_result": {
                "source_word": "xyz123invalid",
                "target_language": Language.SPANISH,
                "source_language": Language.ENGLISH,
                "validation_passed": False,
                "validation_message": "Invalid word: not found in dictionary",
                "suggested_words": [{"word": "valid", "language": Language.ENGLISH}],
            },
            "expected_response_fields": ["status", "validation_result"],
            "expected_notifications": ["processing_started", "validation_failed"],
            "expected_ddb_operations": [],  # Should not store invalid result
        }

    @staticmethod
    def processing_failure_request():
        """Scenario 4: Processing failure - unexpected error."""
        return {
            "request": VocabProcessRequestDto(
                source_word="test",
                target_language="es",
                source_language="en",
                user_id="test_user",
                request_id="test_processing_failure",
            ),
            "mock_graph_result": None,  # Will cause real graph to run and potentially fail
            "expected_response_fields": ["status", "error"],
            "expected_notifications": ["processing_started", "processing_failed"],
            "expected_ddb_operations": [],
        }

    @staticmethod
    def websocket_connect_event():
        """WebSocket connect event."""
        return {
            "requestContext": {
                "connectionId": "test_conn_123",
                "routeKey": "$connect",
                "domainName": "test.execute-api.us-east-1.amazonaws.com",
                "stage": "test",
            },
            "queryStringParameters": {
                "user_id": "test_user",
                "source_word": "hello",
                "target_language": "es",
            },
        }

    @staticmethod
    def websocket_subscribe_event():
        """WebSocket subscribe event."""
        return {
            "requestContext": {"connectionId": "test_conn_123", "routeKey": "$default"},
            "body": json.dumps(
                {
                    "action": "subscribe",
                    "source_word": "hello",
                    "target_language": "es",
                }
            ),
        }

    @staticmethod
    def websocket_disconnect_event():
        """WebSocket disconnect event."""
        return {
            "requestContext": {
                "connectionId": "test_conn_123",
                "routeKey": "$disconnect",
            }
        }


# Example usage and test runner
async def run_integration_tests():
    """Run all integration tests."""
    framework = IntegrationTestFramework()
    results = []

    console.print("[cyan]Running Lambda Integration Tests...[/cyan]")

    # Test Scenario 1: New vocab request
    console.print("Testing: New vocab request...")
    scenario = TestScenarios.new_vocab_request()
    result = await framework.test_lambda_scenario(scenario["request"])
    results.append(result)

    # Verify expected notifications
    framework.assert_notification_sent(
        result.websocket_notifications, "processing_started"
    )
    if not result.error:
        framework.assert_notification_sent(
            result.websocket_notifications, "processing_completed"
        )

    # Test Scenario 2: Existing word request
    console.print("Testing: Existing word request...")
    scenario = TestScenarios.existing_word_request()
    result = await framework.test_lambda_scenario(
        scenario["request"], scenario["mock_graph_result"]
    )
    results.append(result)

    # Verify DDB hit notification
    framework.assert_notification_sent(result.websocket_notifications, "ddb_hit")

    # Test Scenario 3: Invalid word request
    console.print("Testing: Invalid word request...")
    scenario = TestScenarios.invalid_word_request()
    result = await framework.test_lambda_scenario(
        scenario["request"], scenario["mock_graph_result"]
    )
    results.append(result)

    # Verify validation failed notification
    framework.assert_notification_sent(
        result.websocket_notifications, "validation_failed"
    )

    console.print("[cyan]Running WebSocket Integration Tests...[/cyan]")

    # Test WebSocket connect
    console.print("Testing: WebSocket connect...")
    connect_event = TestScenarios.websocket_connect_event()
    ws_result = framework.test_websocket_scenario(connect_event)
    console.print(f"WebSocket Connect Result: {ws_result.response}")

    # Test WebSocket subscribe
    console.print("Testing: WebSocket subscribe...")
    subscribe_event = TestScenarios.websocket_subscribe_event()
    ws_result = framework.test_websocket_scenario(subscribe_event)
    console.print(f"WebSocket Subscribe Result: {ws_result.response}")

    # Test WebSocket disconnect
    console.print("Testing: WebSocket disconnect...")
    disconnect_event = TestScenarios.websocket_disconnect_event()
    ws_result = framework.test_websocket_scenario(disconnect_event)
    console.print(f"WebSocket Disconnect Result: {ws_result.response}")

    # Print results
    framework.print_test_results(results)

    return results


if __name__ == "__main__":
    asyncio.run(run_integration_tests())
