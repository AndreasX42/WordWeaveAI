"""
Test setup module for integration tests.
This module handles AWS mocking and environment setup before any imports.
"""

import os
import sys
from unittest.mock import MagicMock, patch

# Set up environment variables first
os.environ.setdefault("AWS_REGION", "us-east-1")
os.environ.setdefault("DYNAMODB_VOCAB_TABLE_NAME", "test-vocab-table")
os.environ.setdefault("DYNAMODB_CONNECTIONS_TABLE_NAME", "test-connections-table")
os.environ.setdefault("DYNAMODB_VOCAB_MEDIA_TABLE_NAME", "test-media-table")
os.environ.setdefault(
    "WEBSOCKET_API_ENDPOINT", "wss://test.execute-api.us-east-1.amazonaws.com/test"
)
os.environ.setdefault("S3_MEDIA_BUCKET_NAME", "test-media-bucket")
os.environ.setdefault("LAMBDA_PROCESSING_TIMEOUT", "60")

# Add the project root directory to the Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

# Global mocks to be used by tests
_mock_dynamodb_resource = None
_mock_api_gateway_client = None
_mock_s3_client = None
_patchers = []


def setup_aws_mocks():
    """Set up global AWS mocks."""
    global _mock_dynamodb_resource, _mock_api_gateway_client, _mock_s3_client, _patchers

    # Create mock DynamoDB resource
    _mock_dynamodb_resource = MagicMock()

    # Set up DynamoDB table mock with proper return values
    mock_table = MagicMock()
    mock_table.put_item.return_value = {"ResponseMetadata": {"HTTPStatusCode": 200}}
    mock_table.get_item.return_value = {"Item": {}}
    mock_table.query.return_value = {"Items": [], "Count": 0}
    mock_table.scan.return_value = {"Items": [], "Count": 0}
    mock_table.update_item.return_value = {"ResponseMetadata": {"HTTPStatusCode": 200}}
    mock_table.delete_item.return_value = {"ResponseMetadata": {"HTTPStatusCode": 200}}

    _mock_dynamodb_resource.Table.return_value = mock_table

    # Create mock API Gateway client with proper call tracking
    _mock_api_gateway_client = MagicMock()
    _mock_api_gateway_client.post_to_connection = MagicMock(
        return_value={"StatusCode": 200}
    )

    # Create mock S3 client
    _mock_s3_client = MagicMock()

    # Patch boto3 methods
    dynamodb_patcher = patch("boto3.resource")
    api_gateway_patcher = patch("boto3.client")

    # Start patchers
    mock_resource = dynamodb_patcher.start()
    mock_client = api_gateway_patcher.start()

    # Configure return values
    def mock_resource_factory(service_name, **kwargs):
        if service_name == "dynamodb":
            return _mock_dynamodb_resource
        return MagicMock()

    def mock_client_factory(service_name, **kwargs):
        if service_name == "apigatewaymanagementapi":
            return _mock_api_gateway_client
        elif service_name == "s3":
            return _mock_s3_client
        return MagicMock()

    mock_resource.side_effect = mock_resource_factory
    mock_client.side_effect = mock_client_factory

    # Store patchers for cleanup
    _patchers = [dynamodb_patcher, api_gateway_patcher]

    return {
        "dynamodb": _mock_dynamodb_resource,
        "api_gateway": _mock_api_gateway_client,
        "s3": _mock_s3_client,
    }


def cleanup_aws_mocks():
    """Clean up AWS mocks."""
    global _patchers
    for patcher in _patchers:
        patcher.stop()
    _patchers = []


def get_mock_services():
    """Get the mock services."""
    return {
        "dynamodb": _mock_dynamodb_resource,
        "api_gateway": _mock_api_gateway_client,
        "s3": _mock_s3_client,
    }


# Initialize mocks immediately
setup_aws_mocks()
