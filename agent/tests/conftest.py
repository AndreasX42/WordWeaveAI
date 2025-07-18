"""Test configuration for pytest."""

import os

# Set up environment variables for testing
os.environ["DYNAMODB_VOCAB_TABLE_NAME"] = "test-vocab-table"
os.environ["DYNAMODB_VOCAB_MEDIA_TABLE_NAME"] = "test-media-table"
os.environ["AWS_REGION"] = "us-east-1"

# Configure pytest asyncio mode to avoid fixture scope issues
pytest_plugins = ["pytest_asyncio"]
