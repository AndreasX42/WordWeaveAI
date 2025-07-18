"""
Configuration for integration tests with LocalStack.
"""

import os

import pytest
from dotenv import load_dotenv


@pytest.fixture(scope="session", autouse=True)
def load_env_for_integration_tests():
    """Load environment variables for integration tests"""
    # Load .env file if it exists
    load_dotenv()

    # Set up environment variables for LocalStack
    os.environ.update(
        {
            "AWS_ENDPOINT_URL": "http://localhost:4566",
            "AWS_ACCESS_KEY_ID": "test",
            "AWS_SECRET_ACCESS_KEY": "test",
            "AWS_DEFAULT_REGION": "us-east-1",
            "AWS_REGION": "us-east-1",
            "DYNAMODB_VOCAB_TABLE_NAME": "test-vocab-table",
            "DYNAMODB_VOCAB_MEDIA_TABLE_NAME": "test-vocab-media-table",
            "S3_MEDIA_BUCKET_NAME": "test-vocab-media-bucket",
            "SQS_QUEUE_URL": "http://localhost:4566/000000000000/test-vocab-processing-queue",
            "LAMBDA_PROCESSING_TIMEOUT": "180",
            # Force Lambda context for real API calls
            "AWS_LAMBDA_FUNCTION_NAME": "test-vocab-processor",
            # Test mode to skip certain validations
            "INTEGRATION_TEST_MODE": "true",
        }
    )


@pytest.fixture(scope="session")
def check_localstack_running():
    """Check if LocalStack is running before starting tests"""
    import requests

    try:
        response = requests.get("http://localhost:4566/_localstack/health", timeout=5)
        if response.status_code != 200:
            pytest.skip(
                "LocalStack is not running. Start it with: docker-compose up -d"
            )
    except requests.exceptions.RequestException:
        pytest.skip("LocalStack is not running. Start it with: docker-compose up -d")


@pytest.fixture(scope="session")
def wait_for_localstack():
    """Wait for LocalStack to be fully ready"""
    import time

    import requests

    max_retries = 30
    retry_delay = 2

    for attempt in range(max_retries):
        try:
            response = requests.get(
                "http://localhost:4566/_localstack/health", timeout=5
            )
            if response.status_code == 200:
                health_data = response.json()
                # Check if core services are running
                required_services = ["dynamodb", "s3", "sqs", "lambda"]
                if all(
                    service in health_data.get("services", {})
                    for service in required_services
                ):
                    # Additional wait for services to be fully ready
                    time.sleep(3)
                    return
        except requests.exceptions.RequestException:
            pass

        if attempt < max_retries - 1:
            time.sleep(retry_delay)

    pytest.skip("LocalStack did not become ready in time")


@pytest.fixture(autouse=True)
def ensure_localstack_dependencies(check_localstack_running, wait_for_localstack):
    """Ensure LocalStack dependencies are ready before each test"""


# Configure pytest asyncio mode for integration tests
pytest_plugins = ["pytest_asyncio"]
