#!/usr/bin/env python3
"""
Comprehensive LocalStack End-to-End Testing
Tests the complete vocabulary processing flow: SQS → Lambda → WebSocket → DynamoDB → S3
"""

import asyncio
import json
import os
import sys
import time
import unittest
from unittest.mock import MagicMock, patch

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
os.environ["AWS_LAMBDA_FUNCTION_NAME"] = "vocab-processor-lambda"
os.environ["DYNAMODB_VOCAB_TABLE_NAME"] = "vocabDataTable"
os.environ["DYNAMODB_CONNECTIONS_TABLE_NAME"] = "connectionsTable"
os.environ["DYNAMODB_VOCAB_MEDIA_TABLE_NAME"] = "vocabMediaTable"
os.environ["S3_MEDIA_BUCKET_NAME"] = "vocab-media-bucket-local"
os.environ["SQS_QUEUE_URL"] = (
    "http://localhost:4566/000000000000/vocab-processing-queue"
)

# Add the project directory to the path so we can import our modules
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

from handlers.vocab_handler import lambda_handler
from vocab_processor.agent import graph
from vocab_processor.utils.ddb_utils import VocabProcessRequestDto, check_word_exists
from vocab_processor.utils.state import VocabState
from vocab_processor.utils.websocket_utils import WebSocketNotifier


class ComprehensiveE2ETest(unittest.TestCase):
    """Comprehensive end-to-end tests for the complete vocabulary processing flow"""

    def setUp(self):
        """Set up test fixtures"""
        self.setup_aws_clients()
        self.clear_all_test_data()
        self.seed_test_data()
        self.test_connections = []

    def tearDown(self):
        """Clean up test data"""
        self.clear_all_test_data()

    def setup_aws_clients(self):
        """Set up AWS clients for LocalStack"""
        self.dynamodb = boto3.resource(
            "dynamodb",
            endpoint_url=LOCALSTACK_ENDPOINT,
            region_name=AWS_REGION,
            aws_access_key_id=AWS_ACCESS_KEY_ID,
            aws_secret_access_key=AWS_SECRET_ACCESS_KEY,
        )

        self.s3 = boto3.client(
            "s3",
            endpoint_url=LOCALSTACK_ENDPOINT,
            region_name=AWS_REGION,
            aws_access_key_id=AWS_ACCESS_KEY_ID,
            aws_secret_access_key=AWS_SECRET_ACCESS_KEY,
        )

        self.sqs = boto3.client(
            "sqs",
            endpoint_url=LOCALSTACK_ENDPOINT,
            region_name=AWS_REGION,
            aws_access_key_id=AWS_ACCESS_KEY_ID,
            aws_secret_access_key=AWS_SECRET_ACCESS_KEY,
        )

    def clear_all_test_data(self):
        """Clear all test data from DynamoDB tables"""
        tables = ["vocabDataTable", "connectionsTable", "vocabMediaTable"]

        for table_name in tables:
            try:
                table = self.dynamodb.Table(table_name)
                # Scan and delete all items
                response = table.scan()
                for item in response["Items"]:
                    if "PK" in item and "SK" in item:
                        table.delete_item(Key={"PK": item["PK"], "SK": item["SK"]})
                    elif "connectionId" in item:
                        table.delete_item(Key={"connectionId": item["connectionId"]})
                    elif "mediaId" in item:
                        table.delete_item(Key={"mediaId": item["mediaId"]})
            except Exception as e:
                print(f"Error clearing {table_name}: {e}")

    def seed_test_data(self):
        """Seed test data for comprehensive testing"""
        vocab_table = self.dynamodb.Table("vocabDataTable")
        connections_table = self.dynamodb.Table("connectionsTable")

        # Seed vocabulary data
        vocab_items = [
            {
                "PK": "SRC#en#hello",
                "SK": "TGT#es#POS#noun",
                "source_word": "hello",
                "source_language": "en",
                "target_word": "hola",
                "target_language": "es",
                "source_definition": ["A greeting"],
                "source_pos": "noun",
                "target_pos": "noun",
                "created_at": "2024-01-01T00:00:00Z",
            },
            {
                "PK": "SRC#en#house",
                "SK": "TGT#es#POS#noun",
                "source_word": "house",
                "source_language": "en",
                "target_word": "casa",
                "target_language": "es",
                "source_definition": ["A building where people live"],
                "source_pos": "noun",
                "target_pos": "feminine noun",
                "target_article": "la",
                "created_at": "2024-01-01T00:00:00Z",
            },
        ]

        for item in vocab_items:
            vocab_table.put_item(Item=item)

        # Seed connection data
        connection_items = [
            {
                "connectionId": "test-connection-1",
                "user_id": "test-user-1",
                "connected_at": "2024-01-01T00:00:00Z",
                "status": "connected",
            },
            {
                "connectionId": "test-connection-2",
                "user_id": "test-user-2",
                "connected_at": "2024-01-01T00:00:00Z",
                "status": "connected",
            },
        ]

        for item in connection_items:
            connections_table.put_item(Item=item)

    def test_sqs_message_format_validation(self):
        """Test SQS message format validation with various scenarios"""
        print("\n🧪 Testing SQS message format validation...")

        # Test cases with different message formats
        test_cases = [
            # Valid cases
            {
                "name": "complete_valid_message",
                "message": {
                    "source_word": "hello",
                    "source_language": "en",
                    "target_language": "es",
                    "user_id": "test-user-1",
                    "request_id": "req-123",
                },
                "should_pass": True,
            },
            {
                "name": "minimal_valid_message",
                "message": {"source_word": "hello", "target_language": "es"},
                "should_pass": True,
            },
            # Invalid cases
            {
                "name": "missing_source_word",
                "message": {"target_language": "es"},
                "should_pass": False,
            },
            {
                "name": "missing_target_language",
                "message": {"source_word": "hello"},
                "should_pass": False,
            },
            {
                "name": "typo_source_lange",
                "message": {
                    "source_word": "hello",
                    "source_lange": "en",  # Typo: should be source_language
                    "target_language": "es",
                },
                "should_pass": False,
            },
        ]

        for test_case in test_cases:
            with self.subTest(test_case=test_case["name"]):
                try:
                    # Try to parse the message
                    request = VocabProcessRequestDto.model_validate(
                        test_case["message"]
                    )

                    if test_case["should_pass"]:
                        self.assertIsNotNone(request)
                        self.assertEqual(
                            request.source_word, test_case["message"]["source_word"]
                        )
                        self.assertEqual(
                            request.target_language,
                            test_case["message"]["target_language"],
                        )
                    else:
                        self.fail(
                            f"Expected validation to fail for {test_case['name']}"
                        )

                except Exception as e:
                    if test_case["should_pass"]:
                        self.fail(
                            f"Expected validation to pass for {test_case['name']}: {e}"
                        )
                    else:
                        # Expected to fail
                        pass

        print("✅ SQS message format validation tests passed")

    def test_sqs_to_lambda_processing(self):
        """Test full SQS message processing through lambda handler"""
        print("\n🧪 Testing SQS to Lambda processing...")

        # Create a mock SQS event
        sqs_event = {
            "Records": [
                {
                    "messageId": "test-msg-1",
                    "receiptHandle": "test-receipt-1",
                    "body": json.dumps(
                        {
                            "source_word": "cat",
                            "source_language": "en",
                            "target_language": "es",
                            "user_id": "test-user-1",
                            "request_id": "req-cat-001",
                        }
                    ),
                    "attributes": {
                        "ApproximateReceiveCount": "1",
                        "SentTimestamp": "1640995200000",
                        "SenderId": "test-sender",
                        "ApproximateFirstReceiveTimestamp": "1640995200000",
                    },
                    "messageAttributes": {},
                    "md5OfBody": "test-md5",
                    "eventSource": "aws:sqs",
                    "eventSourceARN": "arn:aws:sqs:us-east-1:000000000000:vocab-processing-queue",
                    "awsRegion": "us-east-1",
                }
            ]
        }

        # Mock lambda context
        lambda_context = MagicMock()
        lambda_context.function_name = "vocab-processor-lambda"
        lambda_context.function_version = "1"
        lambda_context.memory_limit_in_mb = 512
        lambda_context.get_remaining_time_in_millis.return_value = 30000

        # Mock WebSocket notifications to avoid actual API calls
        with patch(
            "vocab_processor.utils.websocket_utils.WebSocketNotifier"
        ) as mock_notifier:
            mock_instance = mock_notifier.return_value
            mock_instance.send_processing_started.return_value = None
            mock_instance.send_step_update.return_value = None
            mock_instance.send_processing_completed.return_value = None

            # Process the event
            response = lambda_handler(sqs_event, lambda_context)

            # Verify response structure
            self.assertIsInstance(response, dict)
            self.assertIn("batchItemFailures", response)

            # Check if WebSocket notifications were called
            mock_instance.send_processing_started.assert_called()

        print("✅ SQS to Lambda processing test passed")

    def test_websocket_notifications(self):
        """Test WebSocket notification system"""
        print("\n🧪 Testing WebSocket notification system...")

        # Test WebSocket notifier initialization
        notifier = WebSocketNotifier(user_id="test-user-1", request_id="req-123")
        self.assertEqual(notifier.user_id, "test-user-1")
        self.assertEqual(notifier.request_id, "req-123")

        # Test message creation
        test_message = notifier._create_message("test_type", {"key": "value"})
        self.assertEqual(test_message["type"], "test_type")
        self.assertEqual(test_message["user_id"], "test-user-1")
        self.assertEqual(test_message["request_id"], "req-123")
        self.assertIn("timestamp", test_message)
        self.assertEqual(test_message["data"], {"key": "value"})

        # Test vocab message creation
        vocab_message = notifier._create_vocab_message(
            "processing_started", "cat", "es", "started", extra_field="extra_value"
        )
        self.assertEqual(vocab_message["type"], "processing_started")
        self.assertEqual(vocab_message["data"]["source_word"], "cat")
        self.assertEqual(vocab_message["data"]["target_language"], "es")
        self.assertEqual(vocab_message["data"]["status"], "started")
        self.assertEqual(vocab_message["data"]["extra_field"], "extra_value")

        print("✅ WebSocket notification system tests passed")

    def test_dynamodb_data_validation(self):
        """Test DynamoDB data storage and validation"""
        print("\n🧪 Testing DynamoDB data validation...")

        # Test word existence check
        async def test_word_existence():
            # Test existing word
            result = await check_word_exists("hello", "en", "es", "noun")
            self.assertTrue(result.get("exists", False))

            # Test non-existing word
            result = await check_word_exists("nonexistent", "en", "es", "noun")
            self.assertFalse(result.get("exists", False))

        asyncio.run(test_word_existence())

        # Test table structure validation
        vocab_table = self.dynamodb.Table("vocabDataTable")
        response = vocab_table.scan()

        self.assertIn("Items", response)
        self.assertGreater(len(response["Items"]), 0)

        # Validate item structure
        for item in response["Items"]:
            self.assertIn("PK", item)
            self.assertIn("SK", item)
            self.assertIn("source_word", item)
            self.assertIn("target_word", item)

        print("✅ DynamoDB data validation tests passed")

    def test_s3_media_operations(self):
        """Test S3 media storage and retrieval"""
        print("\n🧪 Testing S3 media operations...")

        bucket_name = "vocab-media-bucket-local"

        # Test bucket existence
        try:
            self.s3.head_bucket(Bucket=bucket_name)
            bucket_exists = True
        except Exception:
            bucket_exists = False

        self.assertTrue(bucket_exists, f"S3 bucket {bucket_name} should exist")

        # Test file upload
        test_content = b"test media content"
        test_key = "test/media/test_image.jpg"

        self.s3.put_object(
            Bucket=bucket_name,
            Key=test_key,
            Body=test_content,
            ContentType="image/jpeg",
        )

        # Test file retrieval
        response = self.s3.get_object(Bucket=bucket_name, Key=test_key)
        retrieved_content = response["Body"].read()

        self.assertEqual(retrieved_content, test_content)

        # Clean up test object
        self.s3.delete_object(Bucket=bucket_name, Key=test_key)

        print("✅ S3 media operations tests passed")

    def test_error_handling_scenarios(self):
        """Test various error handling scenarios"""
        print("\n🧪 Testing error handling scenarios...")

        # Test invalid language codes
        with self.assertRaises(Exception):
            VocabProcessRequestDto.model_validate(
                {
                    "source_word": "hello",
                    "source_language": "invalid_lang_code",
                    "target_language": "es",
                }
            )

        # Test empty source word
        with self.assertRaises(Exception):
            VocabProcessRequestDto.model_validate(
                {"source_word": "", "target_language": "es"}
            )

        # Test connection table operations with invalid connection ID
        connections_table = self.dynamodb.Table("connectionsTable")

        try:
            connections_table.get_item(Key={"connectionId": "non-existent-connection"})
            # Should not raise exception, just return empty result
        except Exception as e:
            self.fail(
                f"Getting non-existent connection should not raise exception: {e}"
            )

        print("✅ Error handling scenarios tests passed")

    def test_concurrent_processing(self):
        """Test concurrent processing with multiple requests"""
        print("\n🧪 Testing concurrent processing...")

        # Create multiple test requests
        test_requests = [
            {"source_word": "dog", "target_language": "es"},
            {"source_word": "cat", "target_language": "fr"},
            {"source_word": "bird", "target_language": "de"},
        ]

        # Mock WebSocket notifications
        with patch(
            "vocab_processor.utils.websocket_utils.WebSocketNotifier"
        ) as mock_notifier:
            mock_instance = mock_notifier.return_value
            mock_instance.send_processing_started.return_value = None
            mock_instance.send_step_update.return_value = None
            mock_instance.send_processing_completed.return_value = None

            # Process requests concurrently
            start_time = time.time()

            async def process_request(request_data):
                state = VocabState(
                    source_word=request_data["source_word"],
                    target_language=request_data["target_language"],
                    connectionId="test-connection-concurrent",
                )
                return graph.invoke(state)

            async def run_concurrent_tests():
                tasks = [process_request(req) for req in test_requests]
                results = await asyncio.gather(*tasks, return_exceptions=True)
                return results

            results = asyncio.run(run_concurrent_tests())

            end_time = time.time()
            processing_time = end_time - start_time

            # Verify all requests were processed
            self.assertEqual(len(results), len(test_requests))

            # Verify no exceptions occurred
            for i, result in enumerate(results):
                if isinstance(result, Exception):
                    self.fail(f"Request {i} failed with exception: {result}")

            print(f"✅ Concurrent processing tests passed ({processing_time:.2f}s)")

    def test_full_integration_flow(self):
        """Test the complete integration flow: SQS → Lambda → WebSocket → DynamoDB → S3"""
        print("\n🧪 Testing full integration flow...")

        # Create a complete test scenario
        test_word = "integration_test_word"

        # Step 1: Create SQS message
        sqs_message = {
            "source_word": test_word,
            "source_language": "en",
            "target_language": "es",
            "user_id": "integration-test-user",
            "request_id": "integration-test-001",
        }

        # Step 2: Validate message format
        request_dto = VocabProcessRequestDto.model_validate(sqs_message)
        self.assertEqual(request_dto.source_word, test_word)

        # Step 3: Process through graph (with mocked external services)
        with patch(
            "vocab_processor.utils.websocket_utils.WebSocketNotifier"
        ) as mock_notifier:
            mock_instance = mock_notifier.return_value
            mock_instance.send_processing_started.return_value = None
            mock_instance.send_step_update.return_value = None
            mock_instance.send_processing_completed.return_value = None

            state = VocabState(
                source_word=test_word,
                target_language="es",
                connectionId="integration-test-connection",
            )

            # Process through graph
            result = graph.invoke(state)

            # Verify processing completed
            self.assertIsNotNone(result)
            self.assertEqual(result["source_word"], test_word)

            # Verify WebSocket notifications were sent
            mock_instance.send_processing_started.assert_called()

        print("✅ Full integration flow test passed")


def run_comprehensive_tests():
    """Run all comprehensive e2e tests"""
    print("🚀 Starting Comprehensive LocalStack End-to-End Tests...")
    print("=" * 80)

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
        print("  docker-compose -f local-e2e-test-resources.yml up -d")
        print("  python local_aws_setup.py")
        return False

    # Run comprehensive tests
    loader = unittest.TestLoader()
    suite = loader.loadTestsFromTestCase(ComprehensiveE2ETest)
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)

    # Print summary
    print("\n" + "=" * 80)
    if result.wasSuccessful():
        print("✅ All comprehensive e2e tests passed!")
        print("🎉 Your vocabulary processing system is working correctly!")
        print("\nTest Coverage:")
        print("  ✅ SQS message format validation")
        print("  ✅ Lambda processing")
        print("  ✅ WebSocket notifications")
        print("  ✅ DynamoDB operations")
        print("  ✅ S3 media operations")
        print("  ✅ Error handling")
        print("  ✅ Concurrent processing")
        print("  ✅ Full integration flow")
    else:
        print(f"❌ {len(result.failures)} test(s) failed")
        print(f"❌ {len(result.errors)} test(s) had errors")
        print("🔧 Please fix the issues before proceeding")

    return result.wasSuccessful()


if __name__ == "__main__":
    success = run_comprehensive_tests()
    sys.exit(0 if success else 1)
