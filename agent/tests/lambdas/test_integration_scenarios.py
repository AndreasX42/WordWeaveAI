import asyncio
import json
import os
import sys
from unittest.mock import patch

import pytest

# Add the project root directory to the Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

# Import test setup to initialize AWS mocks
from test_setup import setup_aws_mocks

# Initialize AWS mocks
setup_aws_mocks()

from test_integration import IntegrationTestFramework, TestScenarios

from vocab_processor.constants import Language
from vocab_processor.utils.ddb_utils import VocabProcessRequestDto


class TestLambdaIntegration:
    """Test suite for Lambda integration scenarios."""

    @pytest.fixture
    def framework(self):
        """Create test framework for each test."""
        return IntegrationTestFramework()

    @pytest.mark.asyncio
    async def test_new_vocab_request_full_processing(self, framework):
        """Test Scenario 1: New vocab request should complete full processing."""
        scenario = TestScenarios.new_vocab_request()
        result = await framework.test_lambda_scenario(scenario["request"])

        # Assertions
        assert result.error is None, f"Processing failed: {result.error}"
        assert result.execution_time > 0, "Execution time should be positive"

        # Check response contains expected fields
        for field in scenario["expected_response_fields"]:
            assert field in result.response, f"Missing field: {field}"

        # Check WebSocket notifications
        notification_types = [
            notif["data"]["type"] for notif in result.websocket_notifications
        ]
        assert (
            "processing_started" in notification_types
        ), "Should send processing_started notification"
        assert (
            "processing_completed" in notification_types
        ), "Should send processing_completed notification"

        # Check DDB operations
        ddb_operations = [op["operation"] for op in result.ddb_operations]
        assert "put_item" in ddb_operations, "Should store result in DDB"

    @pytest.mark.asyncio
    async def test_existing_word_ddb_hit(self, framework):
        """Test Scenario 2: Existing word should return DDB hit."""
        scenario = TestScenarios.existing_word_request()
        result = await framework.test_lambda_scenario(
            scenario["request"], scenario["mock_graph_result"]
        )

        # Assertions
        assert result.error is None, f"Processing failed: {result.error}"
        assert (
            result.response.get("status") == "exists"
        ), "Should return 'exists' status"
        assert result.response.get("ddb_hit") is True, "Should indicate DDB hit"

        # Check WebSocket notifications
        notification_types = [
            notif["data"]["type"] for notif in result.websocket_notifications
        ]
        assert "ddb_hit" in notification_types, "Should send ddb_hit notification"

        # Check that no new items were stored (DDB hit means existing word)
        put_operations = [
            op for op in result.ddb_operations if op["operation"] == "put_item"
        ]
        assert len(put_operations) == 0, "Should not store new item for existing word"

    @pytest.mark.asyncio
    async def test_invalid_word_validation_failure(self, framework):
        """Test Scenario 3: Invalid word should fail validation."""
        scenario = TestScenarios.invalid_word_request()
        result = await framework.test_lambda_scenario(
            scenario["request"], scenario["mock_graph_result"]
        )

        # Assertions
        assert result.error is None, f"Processing failed: {result.error}"
        assert (
            result.response.get("status") == "invalid"
        ), "Should return 'invalid' status"
        assert (
            "validation_result" in result.response
        ), "Should include validation result"

        # Check validation result details
        validation_result = result.response["validation_result"]
        assert validation_result["is_valid"] is False, "Should be marked as invalid"
        assert (
            validation_result["issue_message"] is not None
        ), "Should have error message"

        # Check WebSocket notifications
        notification_types = [
            notif["data"]["type"] for notif in result.websocket_notifications
        ]
        assert (
            "validation_failed" in notification_types
        ), "Should send validation_failed notification"

    @pytest.mark.asyncio
    async def test_processing_timeout_scenario(self, framework):
        """Test Scenario 4: Processing timeout should be handled gracefully."""
        # Create a request that would timeout (using a very short timeout)
        request = VocabProcessRequestDto(
            source_word="timeout_test",
            target_language="spanish",
            source_language="english",
            user_id="test_user",
            request_id="test_timeout",
        )

        # Mock the graph to simulate a timeout
        with patch("handlers.vocab_handler.DEFAULT_TIMEOUT", 0.1):  # Very short timeout
            with patch("asyncio.wait_for") as mock_wait_for:
                mock_wait_for.side_effect = asyncio.TimeoutError()

                result = await framework.test_lambda_scenario(request)

                # Should handle timeout gracefully
                assert result.error is not None, "Should have timeout error"
                assert "TimeoutError" in str(result.error), "Should be timeout error"

    @pytest.mark.asyncio
    async def test_quality_gate_failure_scenario(self, framework):
        """Test Scenario 5: Quality gate failure should stop processing."""
        # Mock a result where quality gates fail
        quality_failure_result = {
            "source_word": "quality_test",
            "target_language": Language.SPANISH,
            "source_language": Language.ENGLISH,
            "validation_passed": True,
            "classification_quality_approved": False,  # Quality gate failure
            "translation_quality_approved": False,
            "sequential_quality_passed": False,
            "failed_quality_steps": ["classification", "translation"],
        }

        request = VocabProcessRequestDto(
            source_word="quality_test",
            target_language="spanish",
            source_language="english",
            user_id="test_user",
            request_id="test_quality_failure",
        )

        result = await framework.test_lambda_scenario(request, quality_failure_result)

        # Should stop processing due to quality gate failure
        assert result.error is None, "Should not have error (graceful handling)"
        # Check that processing was stopped due to quality issues
        assert (
            result.response.get("sequential_quality_passed") is False
        ), "Should fail quality gates"


class TestWebSocketIntegration:
    """Test suite for WebSocket integration scenarios."""

    @pytest.fixture
    def framework(self):
        """Create test framework for each test."""
        return IntegrationTestFramework()

    def test_websocket_connect_success(self, framework):
        """Test WebSocket connection with valid parameters."""
        connect_event = TestScenarios.websocket_connect_event()
        result = framework.test_websocket_scenario(connect_event)

        # Assertions
        assert result.error is None, f"Connection failed: {result.error}"
        assert result.response["statusCode"] == 200, "Should return success status"
        assert result.connection_id == "test_conn_123", "Should track connection ID"

    def test_websocket_connect_without_params(self, framework):
        """Test WebSocket connection without optional parameters."""
        connect_event = {
            "requestContext": {
                "connectionId": "test_conn_456",
                "routeKey": "$connect",
                "domainName": "test.execute-api.us-east-1.amazonaws.com",
                "stage": "test",
            },
            "queryStringParameters": {
                "user_id": "test_user"
                # Missing source_word and target_language
            },
        }

        result = framework.test_websocket_scenario(connect_event)

        # Should still succeed (optional params)
        assert result.error is None, f"Connection failed: {result.error}"
        assert result.response["statusCode"] == 200, "Should return success status"

    def test_websocket_subscribe_success(self, framework):
        """Test WebSocket subscription to vocab word updates."""
        subscribe_event = TestScenarios.websocket_subscribe_event()
        result = framework.test_websocket_scenario(subscribe_event)

        # Assertions
        assert result.error is None, f"Subscription failed: {result.error}"
        assert result.response["statusCode"] == 200, "Should return success status"
        assert result.action == "subscribe", "Should track subscription action"

    def test_websocket_subscribe_invalid_params(self, framework):
        """Test WebSocket subscription with missing parameters."""
        subscribe_event = {
            "requestContext": {"connectionId": "test_conn_123", "routeKey": "$default"},
            "body": json.dumps(
                {
                    "action": "subscribe"
                    # Missing source_word and target_language
                }
            ),
        }

        result = framework.test_websocket_scenario(subscribe_event)

        # Should fail with missing params
        assert result.response["statusCode"] == 400, "Should return bad request status"

    def test_websocket_disconnect_success(self, framework):
        """Test WebSocket disconnection."""
        disconnect_event = TestScenarios.websocket_disconnect_event()
        result = framework.test_websocket_scenario(disconnect_event)

        # Assertions
        assert result.error is None, f"Disconnection failed: {result.error}"
        assert result.response["statusCode"] == 200, "Should return success status"

    def test_websocket_unknown_action(self, framework):
        """Test WebSocket with unknown action."""
        unknown_event = {
            "requestContext": {"connectionId": "test_conn_123", "routeKey": "$default"},
            "body": json.dumps({"action": "unknown_action"}),
        }

        result = framework.test_websocket_scenario(unknown_event)

        # Should return bad request for unknown action
        assert result.response["statusCode"] == 400, "Should return bad request status"


class TestEndToEndIntegration:
    """Test suite for end-to-end integration scenarios."""

    @pytest.fixture
    def framework(self):
        """Create test framework for each test."""
        return IntegrationTestFramework()

    @pytest.mark.asyncio
    async def test_complete_vocab_workflow_with_websocket(self, framework):
        """Test complete workflow: WebSocket connection -> Lambda processing -> Notifications."""
        # Step 1: Connect WebSocket
        connect_event = TestScenarios.websocket_connect_event()
        ws_result = framework.test_websocket_scenario(connect_event)
        assert (
            ws_result.response["statusCode"] == 200
        ), "WebSocket connection should succeed"

        # Step 2: Subscribe to vocab word
        subscribe_event = TestScenarios.websocket_subscribe_event()
        ws_result = framework.test_websocket_scenario(subscribe_event)
        assert (
            ws_result.response["statusCode"] == 200
        ), "WebSocket subscription should succeed"

        # Step 3: Process vocab request
        scenario = TestScenarios.new_vocab_request()
        lambda_result = await framework.test_lambda_scenario(scenario["request"])
        assert lambda_result.error is None, "Lambda processing should succeed"

        # Step 4: Verify notifications were sent
        notification_types = [
            notif["data"]["type"] for notif in lambda_result.websocket_notifications
        ]
        assert (
            "processing_started" in notification_types
        ), "Should notify processing started"
        assert (
            "processing_completed" in notification_types
        ), "Should notify processing completed"

        # Step 5: Verify connections are cleaned up after processing
        # (In real scenario, connections would be closed after processing completes)
        close_notifications = [
            notif
            for notif in lambda_result.websocket_notifications
            if notif["data"]["type"] == "connection_close"
        ]
        # Note: In the mock, this might not be fully simulated

    @pytest.mark.asyncio
    async def test_multiple_concurrent_requests(self, framework):
        """Test multiple concurrent vocab requests."""
        # Create multiple requests
        requests = [
            VocabProcessRequestDto(
                source_word=f"word_{i}",
                target_language="spanish",
                source_language="english",
                user_id=f"user_{i}",
                request_id=f"req_{i}",
            )
            for i in range(3)
        ]

        # Process concurrently
        tasks = [framework.test_lambda_scenario(req) for req in requests]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        # Verify all completed
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                pytest.fail(f"Request {i} failed with exception: {result}")
            assert result.error is None, f"Request {i} should succeed"

    @pytest.mark.asyncio
    async def test_error_handling_chain(self, framework):
        """Test error handling propagation through the system."""
        # Create a request that will fail
        request = VocabProcessRequestDto(
            source_word="",  # Empty word should fail
            target_language="spanish",
            source_language="english",
            user_id="test_user",
            request_id="test_error",
        )

        result = await framework.test_lambda_scenario(request)

        # Should handle error gracefully
        assert result.error is not None, "Should have error for empty word"

        # Check that error notification was sent
        notification_types = [
            notif["data"]["type"] for notif in result.websocket_notifications
        ]
        assert (
            "processing_failed" in notification_types
        ), "Should send processing_failed notification"


# Additional test scenarios for edge cases
class TestEdgeCases:
    """Test suite for edge cases and error conditions."""

    @pytest.fixture
    def framework(self):
        """Create test framework for each test."""
        return IntegrationTestFramework()

    @pytest.mark.asyncio
    async def test_database_connection_failure(self, framework):
        """Test behavior when database connection fails."""
        request = VocabProcessRequestDto(
            source_word="test",
            target_language="spanish",
            source_language="english",
            user_id="test_user",
            request_id="test_db_failure",
        )

        # Mock database failure
        with patch("vocab_processor.utils.ddb_utils.get_vocab_table") as mock_get_table:
            mock_get_table.side_effect = Exception("Database connection failed")

            result = await framework.test_lambda_scenario(request)

            # Should handle database failure gracefully
            assert result.error is not None, "Should have error for database failure"
            assert "Database connection failed" in str(
                result.error
            ), "Should include database error message"

    @pytest.mark.asyncio
    async def test_websocket_notification_failure(self, framework):
        """Test behavior when WebSocket notification fails."""
        request = VocabProcessRequestDto(
            source_word="test",
            target_language="spanish",
            source_language="english",
            user_id="test_user",
            request_id="test_ws_failure",
        )

        # Mock WebSocket failure
        framework.mock_api_gateway.post_to_connection.side_effect = Exception(
            "WebSocket send failed"
        )

        result = await framework.test_lambda_scenario(request)

        # Lambda should still complete even if WebSocket fails
        # (WebSocket failures should not break the main processing)
        assert (
            result.error is None
        ), "Lambda should succeed even with WebSocket failures"

    @pytest.mark.asyncio
    async def test_malformed_request_handling(self, framework):
        """Test handling of malformed requests."""
        # Create request with invalid language
        request = VocabProcessRequestDto(
            source_word="test",
            target_language="invalid_language",  # Invalid language
            source_language="english",
            user_id="test_user",
            request_id="test_malformed",
        )

        result = await framework.test_lambda_scenario(request)

        # Should handle malformed request gracefully
        assert result.error is not None, "Should have error for invalid language"


if __name__ == "__main__":
    # Run tests with pytest
    pytest.main([__file__, "-v"])
