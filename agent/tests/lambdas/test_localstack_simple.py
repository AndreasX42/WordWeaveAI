#!/usr/bin/env python3
"""
Simple LocalStack End-to-End Testing
Tests the core vocabulary processing functionality against LocalStack
"""

import os
import sys
import unittest
from unittest.mock import patch

import boto3

# LocalStack configuration
LOCALSTACK_ENDPOINT = "http://localhost:4566"
AWS_REGION = "us-east-1"
AWS_ACCESS_KEY_ID = "test"
AWS_SECRET_ACCESS_KEY = "test"

# Set up environment variables BEFORE importing modules
os.environ["AWS_ENDPOINT_URL"] = LOCALSTACK_ENDPOINT
os.environ["AWS_ACCESS_KEY_ID"] = AWS_ACCESS_KEY_ID
os.environ["AWS_SECRET_ACCESS_KEY"] = AWS_SECRET_ACCESS_KEY
os.environ["AWS_DEFAULT_REGION"] = AWS_REGION
os.environ["AWS_LAMBDA_FUNCTION_NAME"] = "local-test-function"
os.environ["VOCAB_DATA_TABLE_NAME"] = "vocabDataTable"
os.environ["CONNECTIONS_TABLE_NAME"] = "connectionsTable"
os.environ["S3_MEDIA_BUCKET_NAME"] = "vocab-media-bucket-local"

# Add the project directory to the path so we can import our modules
sys.path.insert(0, os.path.dirname(__file__))

from vocab_processor.agent import graph
from vocab_processor.utils.ddb_utils import check_word_exists
from vocab_processor.utils.state import VocabState


class SimpleLocalStackTest(unittest.TestCase):
    """Simple end-to-end tests against LocalStack"""

    def setUp(self):
        """Set up test fixtures"""
        self.dynamodb = boto3.resource(
            "dynamodb",
            endpoint_url=LOCALSTACK_ENDPOINT,
            region_name=AWS_REGION,
            aws_access_key_id=AWS_ACCESS_KEY_ID,
            aws_secret_access_key=AWS_SECRET_ACCESS_KEY,
        )

        # Clear test data
        self.clear_test_data()

        # Seed test data
        self.seed_test_data()

    def clear_test_data(self):
        """Clear any existing test data"""
        try:
            vocab_table = self.dynamodb.Table("vocabDataTable")

            # Scan and delete all items
            response = vocab_table.scan()
            for item in response["Items"]:
                vocab_table.delete_item(Key={"PK": item["PK"], "SK": item["SK"]})

        except Exception as e:
            print(f"Error clearing test data: {e}")

    def seed_test_data(self):
        """Seed the database with test vocabulary data"""
        vocab_table = self.dynamodb.Table("vocabDataTable")

        # Test vocabulary items
        test_items = [
            {
                "PK": "WORD#hello",
                "SK": "POS#noun",
                "definition": "A greeting",
                "language": "English",
                "partOfSpeech": "noun",
                "created_at": "2024-01-01T00:00:00Z",
            },
            {
                "PK": "WORD#hola",
                "SK": "POS#noun",
                "definition": "A greeting in Spanish",
                "language": "Spanish",
                "partOfSpeech": "noun",
                "created_at": "2024-01-01T00:00:00Z",
            },
        ]

        for item in test_items:
            vocab_table.put_item(Item=item)

    def test_basic_graph_execution(self):
        """Test basic graph execution without WebSocket dependencies"""
        print("\n🧪 Testing basic graph execution...")

        # Test input
        test_input = {
            "source_word": "hello",
            "target_language": "Spanish",
            "connectionId": "test-connection-123",
        }

        # Create initial state
        state = VocabState(
            source_word=test_input["source_word"],
            target_language=test_input["target_language"],
            connectionId=test_input["connectionId"],
        )

        # Mock WebSocket notification methods to avoid actual WebSocket calls
        with patch(
            "vocab_processor.utils.websocket_utils.WebSocketNotifier"
        ) as mock_notifier:
            # Mock all notification methods
            mock_instance = mock_notifier.return_value
            mock_instance.send_ddb_hit.return_value = None
            mock_instance.send_validation_failed.return_value = None
            mock_instance.send_processing_started.return_value = None
            mock_instance.send_processing_completed.return_value = None

            # Run the graph
            result = graph.invoke(state)

        # Verify results
        self.assertIsNotNone(result)
        self.assertEqual(result["source_word"], "hello")

        print("✅ Basic graph execution test passed")

    def test_direct_dynamodb_existence_check(self):
        """Test direct DynamoDB existence check"""
        print("\n🧪 Testing direct DynamoDB existence check...")

        import asyncio

        async def test_async_operations():
            # Test existence check
            result = await check_word_exists("hello", "English", "Spanish", "noun")
            self.assertTrue(
                result.get("exists", False), "Word 'hello' should exist in test data"
            )

            # Test non-existence check
            result = await check_word_exists(
                "nonexistent", "English", "Spanish", "noun"
            )
            self.assertFalse(
                result.get("exists", False), "Word 'nonexistent' should not exist"
            )

        # Run async test
        asyncio.run(test_async_operations())

        print("✅ Direct DynamoDB existence check test passed")

    def test_lambda_context_detection(self):
        """Test Lambda context detection"""
        print("\n🧪 Testing Lambda context detection...")

        from vocab_processor.utils.core_utils import is_lambda_context

        # Test with Lambda environment variable set
        with patch.dict(os.environ, {"AWS_LAMBDA_FUNCTION_NAME": "test-function"}):
            self.assertTrue(is_lambda_context(), "Should detect Lambda context")

        # Test without Lambda environment variable (remove existing one)
        env_backup = os.environ.copy()
        if "AWS_LAMBDA_FUNCTION_NAME" in os.environ:
            del os.environ["AWS_LAMBDA_FUNCTION_NAME"]

        try:
            self.assertFalse(is_lambda_context(), "Should not detect Lambda context")
        finally:
            # Restore environment
            os.environ.clear()
            os.environ.update(env_backup)

        print("✅ Lambda context detection test passed")

    def test_dynamodb_table_access(self):
        """Test that we can access DynamoDB tables"""
        print("\n🧪 Testing DynamoDB table access...")

        vocab_table = self.dynamodb.Table("vocabDataTable")

        # Test table exists and we can query it
        response = vocab_table.scan()
        self.assertIn("Items", response)

        # Should have at least the test data we inserted
        self.assertGreater(len(response["Items"]), 0)

        print(
            f"✅ DynamoDB table access test passed - found {len(response['Items'])} items"
        )

    def test_environment_setup(self):
        """Test that environment variables are set correctly"""
        print("\n🧪 Testing environment setup...")

        # Check required environment variables
        required_vars = [
            "AWS_ENDPOINT_URL",
            "AWS_ACCESS_KEY_ID",
            "AWS_SECRET_ACCESS_KEY",
            "AWS_DEFAULT_REGION",
            "AWS_LAMBDA_FUNCTION_NAME",
            "VOCAB_DATA_TABLE_NAME",
            "CONNECTIONS_TABLE_NAME",
            "S3_MEDIA_BUCKET_NAME",
        ]

        for var in required_vars:
            self.assertIn(var, os.environ, f"Environment variable {var} should be set")

        # Check specific values
        self.assertEqual(os.environ["AWS_ENDPOINT_URL"], LOCALSTACK_ENDPOINT)
        self.assertEqual(os.environ["AWS_DEFAULT_REGION"], AWS_REGION)
        self.assertEqual(os.environ["VOCAB_DATA_TABLE_NAME"], "vocabDataTable")

        print("✅ Environment setup test passed")


def run_simple_tests():
    """Run all simple LocalStack tests"""
    print("🚀 Starting Simple LocalStack End-to-End Tests...")
    print("=" * 60)

    # Check if LocalStack is running
    try:
        sts = boto3.client(
            "sts",
            endpoint_url=LOCALSTACK_ENDPOINT,
            region_name=AWS_REGION,
            aws_access_key_id=AWS_ACCESS_KEY_ID,
            aws_secret_access_key=AWS_SECRET_ACCESS_KEY,
        )
        sts.get_caller_identity()
        print("✅ LocalStack is running")
    except Exception as e:
        print(f"❌ LocalStack is not running: {e}")
        print("Please start LocalStack with:")
        print("  docker-compose up -d")
        print("  python local_aws_setup.py")
        return False

    # Run tests
    loader = unittest.TestLoader()
    suite = loader.loadTestsFromTestCase(SimpleLocalStackTest)
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)

    # Print summary
    print("\n" + "=" * 60)
    if result.wasSuccessful():
        print("✅ All simple LocalStack tests passed!")
        print("🎉 Core functionality is working with LocalStack!")
        print("\nNext steps:")
        print("  - Your DynamoDB operations work correctly")
        print("  - Lambda context detection works")
        print("  - Environment configuration is correct")
        print("  - Ready for AWS deployment testing")
    else:
        print(f"❌ {len(result.failures)} test(s) failed")
        print(f"❌ {len(result.errors)} test(s) had errors")
        print("🔧 Please fix the issues before proceeding")

    return result.wasSuccessful()


if __name__ == "__main__":
    success = run_simple_tests()
    sys.exit(0 if success else 1)
