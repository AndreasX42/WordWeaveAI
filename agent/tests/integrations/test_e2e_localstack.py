"""
E2E Integration Tests using LocalStack

This module contains comprehensive end-to-end integration tests for the vocabulary processor
using LocalStack to mock AWS services. Tests cover:
1. SQS message validation
2. Full SQS->Lambda->DynamoDB+S3 workflows
3. Result verification in DynamoDB and S3
"""

import asyncio
import concurrent.futures
import json
import os
import time
from unittest.mock import patch

import boto3
import pytest

from handlers.vocab_handler import lambda_handler
from vocab_processor.utils.ddb_utils import VocabProcessRequestDto

# Test configuration
LOCALSTACK_ENDPOINT = "http://localhost:4566"
TEST_REGION = "us-east-1"
TEST_VOCAB_TABLE = "test-vocab-table"
TEST_MEDIA_TABLE = "test-vocab-media-table"
TEST_S3_BUCKET = "test-vocab-media-bucket"
TEST_SQS_QUEUE = "test-vocab-processing-queue"


@pytest.fixture(scope="module")
def localstack_setup():
    """Setup LocalStack environment and AWS resources"""
    # Configure environment for LocalStack
    os.environ.update(
        {
            "AWS_ENDPOINT_URL": LOCALSTACK_ENDPOINT,
            "AWS_ACCESS_KEY_ID": "test",
            "AWS_SECRET_ACCESS_KEY": "test",
            "AWS_DEFAULT_REGION": TEST_REGION,
            "AWS_REGION": TEST_REGION,
            "DYNAMODB_VOCAB_TABLE_NAME": TEST_VOCAB_TABLE,
            "DYNAMODB_VOCAB_MEDIA_TABLE_NAME": TEST_MEDIA_TABLE,
            "S3_MEDIA_BUCKET_NAME": TEST_S3_BUCKET,
            "SQS_QUEUE_URL": f"{LOCALSTACK_ENDPOINT}/000000000000/{TEST_SQS_QUEUE}",
            "LAMBDA_PROCESSING_TIMEOUT": "180",
        }
    )

    # Create AWS clients for LocalStack
    clients = {
        "dynamodb": boto3.client(
            "dynamodb", endpoint_url=LOCALSTACK_ENDPOINT, region_name=TEST_REGION
        ),
        "s3": boto3.client(
            "s3", endpoint_url=LOCALSTACK_ENDPOINT, region_name=TEST_REGION
        ),
        "sqs": boto3.client(
            "sqs", endpoint_url=LOCALSTACK_ENDPOINT, region_name=TEST_REGION
        ),
        "lambda": boto3.client(
            "lambda", endpoint_url=LOCALSTACK_ENDPOINT, region_name=TEST_REGION
        ),
    }

    # Create AWS resources
    _create_dynamodb_tables(clients["dynamodb"])
    _create_s3_bucket(clients["s3"])
    _create_sqs_queue(clients["sqs"])

    return clients


def _cleanup_test_data(clients):
    """Clean up test data between tests for better isolation"""
    try:
        # Clear DynamoDB tables
        dynamodb_client = clients["dynamodb"]  # type: ignore

        # Clear Vocab table
        response = dynamodb_client.scan(TableName=TEST_VOCAB_TABLE)
        items = response.get("Items", [])
        for item in items:
            dynamodb_client.delete_item(
                TableName=TEST_VOCAB_TABLE, Key={"PK": item["PK"], "SK": item["SK"]}
            )

        # Clear Media table
        response = dynamodb_client.scan(TableName=TEST_MEDIA_TABLE)
        items = response.get("Items", [])
        for item in items:
            dynamodb_client.delete_item(
                TableName=TEST_MEDIA_TABLE, Key={"PK": item["PK"]}
            )

        print("✅ Test data cleaned up successfully")

    except Exception as e:
        print(f"⚠️  Cleanup failed (non-critical): {e}")


def _create_dynamodb_tables(dynamodb_client):
    """Create DynamoDB tables for testing"""
    # Create Vocab table
    try:
        dynamodb_client.create_table(
            TableName=TEST_VOCAB_TABLE,
            KeySchema=[
                {"AttributeName": "PK", "KeyType": "HASH"},
                {"AttributeName": "SK", "KeyType": "RANGE"},
            ],
            AttributeDefinitions=[
                {"AttributeName": "PK", "AttributeType": "S"},
                {"AttributeName": "SK", "AttributeType": "S"},
                {"AttributeName": "LKP", "AttributeType": "S"},
                {"AttributeName": "SRC_LANG", "AttributeType": "S"},
                {"AttributeName": "english_word", "AttributeType": "S"},
            ],
            BillingMode="PAY_PER_REQUEST",
            GlobalSecondaryIndexes=[
                {
                    "IndexName": "GSI1",
                    "KeySchema": [
                        {"AttributeName": "LKP", "KeyType": "HASH"},
                        {"AttributeName": "SRC_LANG", "KeyType": "RANGE"},
                    ],
                    "Projection": {"ProjectionType": "ALL"},
                },
                {
                    "IndexName": "GSI2",
                    "KeySchema": [
                        {"AttributeName": "english_word", "KeyType": "HASH"},
                    ],
                    "Projection": {"ProjectionType": "ALL"},
                },
            ],
        )
    except Exception as e:
        print(f"Error creating vocab table: {e}")

    # Create Media table (only needs PK, no SK)
    try:
        dynamodb_client.create_table(
            TableName=TEST_MEDIA_TABLE,
            KeySchema=[
                {"AttributeName": "PK", "KeyType": "HASH"},
            ],
            AttributeDefinitions=[
                {"AttributeName": "PK", "AttributeType": "S"},
            ],
            BillingMode="PAY_PER_REQUEST",
        )
    except Exception as e:
        print(f"Error creating media table: {e}")


def _create_s3_bucket(s3_client):
    """Create S3 bucket for testing"""
    try:
        s3_client.create_bucket(Bucket=TEST_S3_BUCKET)
    except Exception as e:
        print(f"Error creating S3 bucket: {e}")


def _create_sqs_queue(sqs_client):
    """Create SQS queue for testing"""
    try:
        sqs_client.create_queue(
            QueueName=TEST_SQS_QUEUE,
            Attributes={
                "VisibilityTimeout": "300",
                "MessageRetentionPeriod": "1209600",
                "DelaySeconds": "0",
            },
        )
    except Exception as e:
        print(f"Error creating SQS queue: {e}")


@pytest.fixture
def force_lambda_context():
    """Override is_lambda_context to return True for real API calls"""
    with patch("vocab_processor.utils.core_utils.is_lambda_context", return_value=True):
        yield


@pytest.fixture
def cleanup_after_test(localstack_setup):
    """Clean up test data after each test for better isolation"""
    yield  # Run the test first
    # Clean up after test
    _cleanup_test_data(localstack_setup)


class TestSQSValidation:
    """Test SQS message validation"""

    def test_valid_sqs_message_parsing(self, localstack_setup):
        """Test that valid SQS messages are parsed correctly"""
        # Test valid message with all required fields
        valid_message = {
            "source_word": "hello",
            "target_language": "es",
            "source_language": "en",
            "user_id": "test-user",
            "request_id": "test-request-123",
        }

        # Should not raise any validation errors
        request = VocabProcessRequestDto(**valid_message)
        assert request.source_word == "hello"
        assert request.target_language == "es"
        assert request.source_language == "en"
        assert request.user_id == "test-user"
        assert request.request_id == "test-request-123"

    def test_valid_sqs_message_minimal(self, localstack_setup):
        """Test valid SQS message with minimal required fields"""
        minimal_message = {"source_word": "build", "target_language": "de"}

        request = VocabProcessRequestDto(**minimal_message)
        assert request.source_word == "build"
        assert request.target_language == "de"
        assert request.source_language is None
        assert request.user_id is None
        assert request.request_id is None

    def test_invalid_target_language(self, localstack_setup):
        """Test that invalid target language codes are rejected"""
        invalid_message = {"source_word": "hello", "target_language": "invalid-lang"}

        with pytest.raises(ValueError) as exc_info:
            VocabProcessRequestDto(**invalid_message)

        assert "Invalid target_language" in str(exc_info.value)

    def test_invalid_source_language(self, localstack_setup):
        """Test that invalid source language codes are rejected"""
        invalid_message = {
            "source_word": "hello",
            "target_language": "es",
            "source_language": "invalid-lang",
        }

        with pytest.raises(ValueError) as exc_info:
            VocabProcessRequestDto(**invalid_message)

        assert "Invalid source_language" in str(exc_info.value)

    def test_empty_source_word(self, localstack_setup):
        """Test that empty source words are rejected"""
        invalid_message = {"source_word": "", "target_language": "es"}

        with pytest.raises(ValueError) as exc_info:
            VocabProcessRequestDto(**invalid_message)

        assert "source_word cannot be empty" in str(exc_info.value)

    def test_whitespace_source_word(self, localstack_setup):
        """Test that whitespace-only source words are rejected"""
        invalid_message = {"source_word": "   ", "target_language": "es"}

        with pytest.raises(ValueError) as exc_info:
            VocabProcessRequestDto(**invalid_message)

        assert "source_word cannot be empty" in str(exc_info.value)

    def test_missing_required_fields(self, localstack_setup):
        """Test that missing required fields are rejected"""
        # Missing source_word
        with pytest.raises(ValueError):
            VocabProcessRequestDto(target_language="es")

        # Missing target_language
        with pytest.raises(ValueError):
            VocabProcessRequestDto(source_word="hello")

    def test_valid_language_codes(self, localstack_setup):
        """Test all valid language codes"""
        valid_codes = ["en", "es", "de"]

        for source_lang in valid_codes:
            for target_lang in valid_codes:
                if source_lang != target_lang:
                    request = VocabProcessRequestDto(
                        source_word="test",
                        source_language=source_lang,
                        target_language=target_lang,
                    )
                    assert request.source_language == source_lang
                    assert request.target_language == target_lang


class TestFullE2E:
    """Test full SQS->Lambda->DynamoDB+S3 workflows"""

    # TODO: Add later, TestResultVerification is more important
    # @pytest.mark.asyncio
    # async def test_e2e_build_english_to_spanish(
    #     self, localstack_setup, force_lambda_context, cleanup_after_test
    # ):
    #     """Test: to build (en) -> es"""
    #     await self._run_e2e_test(
    #         source_word="to build",
    #         target_language="es",
    #         source_language="en",
    #         localstack_setup=localstack_setup,
    #     )

    # @pytest.mark.asyncio
    # async def test_e2e_construct_english_to_german(
    #     self, localstack_setup, force_lambda_context, cleanup_after_test
    # ):
    #     """Test: to construct (en) -> de"""
    #     await self._run_e2e_test(
    #         source_word="to construct",
    #         target_language="de",
    #         source_language="en",
    #         localstack_setup=localstack_setup,
    #     )

    # @pytest.mark.asyncio
    # async def test_e2e_schadenfreude_german_to_english(
    #     self, localstack_setup, force_lambda_context, cleanup_after_test
    # ):
    #     """Test: Schadenfreude (de) -> en"""
    #     await self._run_e2e_test(
    #         source_word="Schadenfreude",
    #         target_language="en",
    #         source_language="de",
    #         localstack_setup=localstack_setup,
    #     )

    async def _run_e2e_test(
        self,
        source_word: str,
        target_language: str,
        source_language: str,
        localstack_setup,
    ):
        """Run a full e2e test for given parameters"""
        # Generate unique identifiers for this test
        test_id = f"{source_word}_{target_language}_{int(time.time() * 1000000)}"

        print(f"🚀 Starting test: {source_word} -> {target_language} at {time.time()}")

        # Create SQS message
        message = {
            "source_word": source_word,
            "target_language": target_language,
            "source_language": source_language,
            "user_id": "test-user",
            "request_id": f"test-{test_id}",
        }

        # Create Lambda event with unique IDs
        lambda_event = {
            "Records": [
                {
                    "messageId": f"test-message-{test_id}",
                    "receiptHandle": f"test-receipt-{test_id}",
                    "body": json.dumps(message),
                    "attributes": {
                        "ApproximateReceiveCount": "1",
                        "SentTimestamp": str(int(time.time() * 1000)),
                        "SenderId": "test-sender",
                        "ApproximateFirstReceiveTimestamp": str(
                            int(time.time() * 1000)
                        ),
                    },
                    "messageAttributes": {},
                    "md5OfBody": "test-md5",
                    "eventSource": "aws:sqs",
                    "eventSourceARN": f"arn:aws:sqs:{TEST_REGION}:000000000000:{TEST_SQS_QUEUE}",
                    "awsRegion": TEST_REGION,
                }
            ]
        }

        # Create mock Lambda context
        class MockLambdaContext:
            def __init__(self):
                self.function_name = "test-vocab-processor"
                self.function_version = "1"
                self.invoked_function_arn = f"arn:aws:lambda:{TEST_REGION}:000000000000:function:test-vocab-processor"
                self.memory_limit_in_mb = 512
                self.remaining_time_in_millis = lambda: 30000
                self.log_group_name = f"/aws/lambda/{self.function_name}"
                self.log_stream_name = "test-log-stream"
                self.aws_request_id = "test-request-id"

        context = MockLambdaContext()

        # Override is_lambda_context to return True for real API calls
        with patch(
            "vocab_processor.utils.core_utils.is_lambda_context", return_value=True
        ):
            # Execute Lambda function asynchronously
            print(f"⚡ Executing Lambda for {source_word} -> {target_language}")

            def run_lambda():
                return lambda_handler(lambda_event, context)

            # Use asyncio.to_thread for better async execution
            result = await asyncio.to_thread(run_lambda)

            # Verify Lambda execution success
            assert result is not None
            assert "batchItemFailures" in result
            assert (
                len(result["batchItemFailures"]) == 0
            ), f"Lambda processing failed: {result}"

        # Wait for processing to complete
        await asyncio.sleep(2)

        # Verify DynamoDB results
        await self._verify_dynamodb_results(
            source_word, target_language, source_language, localstack_setup
        )

        # Verify S3 results
        await self._verify_s3_results(
            source_word, target_language, source_language, localstack_setup
        )

        print(f"✅ Completed test: {source_word} -> {target_language} at {time.time()}")

    async def _verify_dynamodb_results(
        self,
        source_word: str,
        target_language: str,
        source_language: str,
        localstack_setup,
    ):
        """Verify DynamoDB contains expected results"""
        dynamodb = boto3.resource(
            "dynamodb", endpoint_url=LOCALSTACK_ENDPOINT, region_name=TEST_REGION
        )

        # Check Vocab table
        vocab_table = dynamodb.Table(TEST_VOCAB_TABLE)

        # Scan for items (in real test, you'd use more specific queries)
        response = vocab_table.scan()
        items = response.get("Items", [])

        # Should have at least one vocab item
        assert len(items) >= 1, f"Expected at least 1 vocab item, got {len(items)}"

        # Verify item structure
        vocab_item = items[0]  # type: ignore
        assert "PK" in vocab_item
        assert "SK" in vocab_item
        assert "source_word" in vocab_item
        assert "target_word" in vocab_item
        assert "source_language" in vocab_item
        assert "target_language" in vocab_item

        # Check Media table
        media_table = dynamodb.Table(TEST_MEDIA_TABLE)
        media_response = media_table.scan()
        media_items = media_response.get("Items", [])

        # Filter for actual media items (not search term references)
        actual_media_items = [
            item for item in media_items if item["PK"].startswith("MEDIA#")  # type: ignore
        ]

        # Should have at least one actual media item
        assert (
            len(actual_media_items) >= 1
        ), f"Expected at least 1 MEDIA# item, got {len(actual_media_items)}"

        media_item = actual_media_items[0]
        assert "PK" in media_item
        assert media_item["PK"].startswith("MEDIA#")  # type: ignore
        assert "media" in media_item  # Verify it contains actual media data

    async def _verify_s3_results(
        self,
        source_word: str,
        target_language: str,
        source_language: str,
        localstack_setup,
    ):
        """Verify S3 contains expected media files"""
        s3_client = localstack_setup["s3"]  # type: ignore

        # List all objects in bucket
        response = s3_client.list_objects_v2(Bucket=TEST_S3_BUCKET)

        if "Contents" not in response:
            pytest.fail("No objects found in S3 bucket")

        objects = response["Contents"]
        object_keys = [obj["Key"] for obj in objects]

        # Should have audio files (pronunciation.mp3, syllables.mp3)
        audio_files = [key for key in object_keys if key.endswith(".mp3")]
        assert (
            len(audio_files) >= 2
        ), f"Expected at least 2 audio files, got {len(audio_files)}: {audio_files}"

        # Should have image files (medium.jpg, large.jpg, large2x.jpg)
        image_files = [key for key in object_keys if key.endswith(".jpg")]
        assert (
            len(image_files) >= 3
        ), f"Expected at least 3 image files, got {len(image_files)}: {image_files}"

        # Verify total file count (6 audio + 6 images = 12 files per test)
        total_files = len(object_keys)
        assert total_files >= 5, f"Expected at least 5 files total, got {total_files}"


class TestResultVerification:
    """Test result verification utilities"""

    @pytest.mark.asyncio
    async def test_verify_combined_tests_results(
        self, localstack_setup, force_lambda_context
    ):
        """Run all test cases sequentially to test individual processing"""
        test_cases = [
            {
                "source_word": "to build",
                "target_language": "es",
                "source_language": "en",
            },
            {
                "source_word": "to assemble",
                "target_language": "de",
                "source_language": "en",
            },
            {
                "source_word": "construir",
                "target_language": "en",
                "source_language": "es",
            },
            {
                "source_word": "das Haus",
                "target_language": "en",
                "source_language": "de",
            },
        ]

        # Run tests sequentially to ensure proper isolation
        print(f"🔄 Starting {len(test_cases)} tests sequentially at {time.time()}")

        for i, test_case in enumerate(test_cases):
            print(
                f"📋 Running test {i+1}/{len(test_cases)}: {test_case['source_word']} -> {test_case['target_language']}"
            )
            await TestFullE2E()._run_e2e_test(
                source_word=test_case["source_word"],
                target_language=test_case["target_language"],
                source_language=test_case["source_language"],
                localstack_setup=localstack_setup,
            )
            # Add delay between tests to avoid conflicts
            await asyncio.sleep(3)

        print(f"🎉 All {len(test_cases)} tests completed at {time.time()}")

        # Verify final state
        await self._verify_final_state(localstack_setup)

    async def _verify_final_state(self, localstack_setup):
        """Verify final state after all tests"""
        dynamodb = boto3.resource(
            "dynamodb", endpoint_url=LOCALSTACK_ENDPOINT, region_name=TEST_REGION
        )
        s3_client = localstack_setup["s3"]  # type: ignore

        # Check DynamoDB - should have 3 items in Vocab table
        vocab_table = dynamodb.Table(TEST_VOCAB_TABLE)
        vocab_response = vocab_table.scan()
        vocab_items = vocab_response.get("Items", [])
        assert len(vocab_items) == 4, f"Expected 4 vocab items, got {len(vocab_items)}"

        # Check DynamoDB - should have 3 MEDIA# items in VocabMedia table
        media_table = dynamodb.Table(TEST_MEDIA_TABLE)
        media_response = media_table.scan()
        media_items = media_response.get("Items", [])
        media_count = len(
            [item for item in media_items if item["PK"].startswith("MEDIA#")]  # type: ignore
        )
        assert media_count == 3, f"Expected 3 media items, got {media_count}"

        # Check that media_ref values in Vocab table match MEDIA# keys in VocabMedia table
        vocab_media_refs = set()
        for vocab_item in vocab_items:
            if "media_ref" in vocab_item and vocab_item["media_ref"]:  # type: ignore
                vocab_media_refs.add(vocab_item["media_ref"])  # type: ignore

        media_keys = set()
        for media_item in media_items:
            if media_item["PK"].startswith("MEDIA#"):  # type: ignore
                media_keys.add(media_item["PK"])  # type: ignore

        assert vocab_media_refs == media_keys, (
            f"Vocab media_ref values don't match VocabMedia MEDIA# keys. "
            f"Vocab refs: {vocab_media_refs}, Media keys: {media_keys}"
        )

        # Check S3 - should have 6 audio files and 6 image files
        response = s3_client.list_objects_v2(Bucket=TEST_S3_BUCKET)

        if "Contents" not in response:
            pytest.fail("No objects found in S3 bucket")

        objects = response["Contents"]
        object_keys = [obj["Key"] for obj in objects]

        # Count audio and image files
        audio_files = [key for key in object_keys if key.endswith(".mp3")]
        image_files = [key for key in object_keys if key.endswith(".jpg")]

        assert len(audio_files) == 6, f"Expected 6 audio files, got {len(audio_files)}"
        assert len(image_files) == 6, f"Expected 6 image files, got {len(image_files)}"

        print(f"✅ Final verification passed:")
        print(f"  - Vocab items: {len(vocab_items)}")
        print(f"  - Media items: {media_count}")
        print(f"  - Audio files: {len(audio_files)}")
        print(
            f"  - Media references integrity: {len(vocab_media_refs)} refs match {len(media_keys)} keys"
        )
        print(f"  - Image files: {len(image_files)}")
        print(f"  - Total S3 objects: {len(object_keys)}")


class TestErrorHandling:
    """Test error handling scenarios"""

    @pytest.mark.asyncio
    async def test_malformed_sqs_message(self, localstack_setup, cleanup_after_test):
        """Test handling of malformed SQS messages"""
        # Ensure clean state before test
        _cleanup_test_data(localstack_setup)

        # Wait for any pending Lambda processing to complete
        await asyncio.sleep(2)

        # Create malformed Lambda event
        lambda_event = {
            "Records": [
                {
                    "messageId": "malformed-test-message-id",
                    "receiptHandle": "malformed-test-receipt-handle",
                    "body": "invalid-json",  # Malformed JSON
                    "attributes": {
                        "ApproximateReceiveCount": "1",
                        "SentTimestamp": str(int(time.time() * 1000)),
                        "SenderId": "test-sender",
                        "ApproximateFirstReceiveTimestamp": str(
                            int(time.time() * 1000)
                        ),
                    },
                    "messageAttributes": {},
                    "md5OfBody": "test-md5",
                    "eventSource": "aws:sqs",
                    "eventSourceARN": f"arn:aws:sqs:{TEST_REGION}:000000000000:{TEST_SQS_QUEUE}",
                    "awsRegion": TEST_REGION,
                }
            ]
        }

        class MockLambdaContext:
            def __init__(self):
                self.function_name = "test-vocab-processor"
                self.function_version = "1"
                self.invoked_function_arn = f"arn:aws:lambda:{TEST_REGION}:000000000000:function:test-vocab-processor"
                self.memory_limit_in_mb = 512
                self.remaining_time_in_millis = lambda: 30000
                self.log_group_name = f"/aws/lambda/{self.function_name}"
                self.log_stream_name = "test-log-stream"
                self.aws_request_id = "test-request-id"

        context = MockLambdaContext()

        # Execute Lambda function with malformed message
        def run_lambda():
            return lambda_handler(lambda_event, context)

        with concurrent.futures.ThreadPoolExecutor() as executor:
            future = executor.submit(run_lambda)
            result = future.result(timeout=30)  # 30 second timeout for error case

        # Should return batch item failure
        assert "batchItemFailures" in result
        assert len(result["batchItemFailures"]) == 1
        assert (
            result["batchItemFailures"][0]["itemIdentifier"]
            == "malformed-test-message-id"
        )

    @pytest.mark.asyncio
    async def test_validation_failure(self, localstack_setup, force_lambda_context):
        """Test handling of validation failures"""
        # Create message with invalid word
        message = {
            "source_word": "definitely-not-a-real-word-12345",
            "target_language": "es",
            "source_language": "en",
            "user_id": "test-user",
            "request_id": "test-validation-failure",
        }

        lambda_event = {
            "Records": [
                {
                    "messageId": "test-validation-message-id",
                    "receiptHandle": "test-receipt-handle",
                    "body": json.dumps(message),
                    "attributes": {
                        "ApproximateReceiveCount": "1",
                        "SentTimestamp": str(int(time.time() * 1000)),
                        "SenderId": "test-sender",
                        "ApproximateFirstReceiveTimestamp": str(
                            int(time.time() * 1000)
                        ),
                    },
                    "messageAttributes": {},
                    "md5OfBody": "test-md5",
                    "eventSource": "aws:sqs",
                    "eventSourceARN": f"arn:aws:sqs:{TEST_REGION}:000000000000:{TEST_SQS_QUEUE}",
                    "awsRegion": TEST_REGION,
                }
            ]
        }

        class MockLambdaContext:
            def __init__(self):
                self.function_name = "test-vocab-processor"
                self.function_version = "1"
                self.invoked_function_arn = f"arn:aws:lambda:{TEST_REGION}:000000000000:function:test-vocab-processor"
                self.memory_limit_in_mb = 512
                self.remaining_time_in_millis = lambda: 30000
                self.log_group_name = f"/aws/lambda/{self.function_name}"
                self.log_stream_name = "test-log-stream"
                self.aws_request_id = "test-request-id"

        context = MockLambdaContext()

        # Execute Lambda function
        def run_lambda():
            return lambda_handler(lambda_event, context)

        with concurrent.futures.ThreadPoolExecutor() as executor:
            future = executor.submit(run_lambda)
            result = future.result(timeout=30)  # 30 second timeout for error case

        # Should handle validation failure gracefully
        assert result is not None
        assert "batchItemFailures" in result
        # Validation failures should be processed successfully (not cause batch failures)
        # The system should handle invalid words gracefully without batch failures
        assert len(result["batchItemFailures"]) == 0
