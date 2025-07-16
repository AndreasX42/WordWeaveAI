#!/usr/bin/env python3
"""
Simple test script to verify integration tests work with proper AWS mocking.
"""

import asyncio
import os
import sys

# Set up environment variables before importing modules
os.environ["AWS_REGION"] = "us-east-1"
os.environ["DYNAMODB_VOCAB_TABLE_NAME"] = "test-vocab-table"
os.environ["DYNAMODB_CONNECTIONS_TABLE_NAME"] = "test-connections-table"
os.environ["DYNAMODB_VOCAB_MEDIA_TABLE_NAME"] = "test-media-table"
os.environ["WEBSOCKET_API_ENDPOINT"] = (
    "wss://test.execute-api.us-east-1.amazonaws.com/test"
)
os.environ["S3_MEDIA_BUCKET_NAME"] = "test-media-bucket"
os.environ["LAMBDA_PROCESSING_TIMEOUT"] = "60"

# Add the project root directory to the Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

from test_integration import IntegrationTestFramework, TestScenarios


async def test_basic_mocking():
    """Test basic AWS mocking is working."""
    framework = IntegrationTestFramework()

    print("Testing basic framework initialization...")
    assert (
        framework.mock_vocab_table is not None
    ), "Mock vocab table should be initialized"
    assert (
        framework.mock_connections_table is not None
    ), "Mock connections table should be initialized"
    assert (
        framework.mock_media_table is not None
    ), "Mock media table should be initialized"
    assert (
        framework.mock_api_gateway is not None
    ), "Mock API Gateway should be initialized"

    print("✓ Framework initialization successful")


async def test_existing_word_scenario():
    """Test the existing word scenario with mocking."""
    framework = IntegrationTestFramework()

    print("Testing existing word scenario...")
    scenario = TestScenarios.existing_word_request()

    try:
        result = await framework.test_lambda_scenario(
            scenario["request"], scenario["mock_graph_result"]
        )

        print(f"✓ Test completed successfully")
        print(
            f"  - Request: {result.request.source_word} -> {result.request.target_language}"
        )
        print(f"  - Execution time: {result.execution_time:.2f}s")
        print(f"  - WebSocket notifications: {len(result.websocket_notifications)}")
        print(f"  - DDB operations: {len(result.ddb_operations)}")

        if result.error:
            print(f"  - Error: {result.error}")
        else:
            print(f"  - Response status: {result.response.get('status', 'N/A')}")

    except Exception as e:
        print(f"✗ Test failed: {e}")
        raise


async def test_websocket_connect():
    """Test WebSocket connection scenario."""
    framework = IntegrationTestFramework()

    print("Testing WebSocket connection...")
    connect_event = TestScenarios.websocket_connect_event()

    try:
        result = framework.test_websocket_scenario(connect_event)

        print(f"✓ WebSocket test completed")
        print(f"  - Connection ID: {result.connection_id}")
        print(f"  - Response status: {result.response.get('statusCode', 'N/A')}")

        if result.error:
            print(f"  - Error: {result.error}")

    except Exception as e:
        print(f"✗ WebSocket test failed: {e}")
        raise


async def main():
    """Run all tests."""
    print("🧪 Running Integration Test Verification...")
    print("=" * 50)

    try:
        await test_basic_mocking()
        print()

        await test_existing_word_scenario()
        print()

        await test_websocket_connect()
        print()

        print("🎉 All tests passed successfully!")

    except Exception as e:
        print(f"❌ Test suite failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
