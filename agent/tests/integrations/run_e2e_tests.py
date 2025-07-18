#!/usr/bin/env python3
"""
E2E Test Runner for LocalStack Integration Tests

This script sets up and runs the end-to-end integration tests using LocalStack.
It handles environment setup, LocalStack health checks, and test execution.
"""

import argparse
import os
import subprocess
import sys
import time
from pathlib import Path
from typing import List, Optional

import requests
from dotenv import load_dotenv


def check_localstack_health(max_retries: int = 30, retry_delay: float = 2.0) -> bool:
    """Check if LocalStack is healthy and ready."""
    print("🔍 Checking LocalStack health...")

    for attempt in range(max_retries):
        try:
            response = requests.get(
                "http://localhost:4566/_localstack/health", timeout=5
            )
            if response.status_code == 200:
                health_data = response.json()
                services = health_data.get("services", {})

                # Check required services
                required_services = ["dynamodb", "s3", "sqs", "lambda"]
                ready_services = [svc for svc in required_services if svc in services]

                if len(ready_services) == len(required_services):
                    print(f"✅ LocalStack is healthy! Services ready: {ready_services}")
                    return True
                else:
                    missing = set(required_services) - set(ready_services)
                    print(f"⏳ Waiting for services: {missing}")

        except requests.exceptions.RequestException as e:
            print(f"⏳ Attempt {attempt + 1}/{max_retries}: LocalStack not ready ({e})")

        if attempt < max_retries - 1:
            time.sleep(retry_delay)

    print("❌ LocalStack health check failed")
    return False


def setup_environment():
    """Set up environment variables for testing."""
    print("🔧 Setting up environment variables...")

    # Load .env file if it exists
    load_dotenv()

    # Set up test environment
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
            # Test mode
            "INTEGRATION_TEST_MODE": "true",
        }
    )

    print("✅ Environment variables set up")


def run_pytest_command(
    test_path: Optional[str] = None, extra_args: List[str] = None
) -> int:
    """Run pytest with the specified configuration."""
    print("🧪 Running integration tests...")

    # Build pytest command
    cmd = [
        sys.executable,
        "-m",
        "pytest",
        "-v",
        "--tb=short",
        "--asyncio-mode=auto",
        "-s",  # Don't capture output for real-time feedback
    ]

    if test_path:
        cmd.append(test_path)
    else:
        cmd.append("tests/integrations/test_e2e_localstack.py")

    if extra_args:
        cmd.extend(extra_args)

    print(f"Running command: {' '.join(cmd)}")

    # Run pytest
    result = subprocess.run(cmd, cwd=Path(__file__).parent.parent.parent)
    return result.returncode


def main():
    """Main function to run the e2e tests."""
    parser = argparse.ArgumentParser(
        description="Run E2E Integration Tests with LocalStack"
    )
    parser.add_argument(
        "--test-path",
        "-t",
        help="Specific test path to run (default: run all e2e tests)",
    )
    parser.add_argument(
        "--skip-health-check",
        "-s",
        action="store_true",
        help="Skip LocalStack health check",
    )
    parser.add_argument(
        "--pytest-args",
        nargs=argparse.REMAINDER,
        help="Additional arguments to pass to pytest",
    )

    args = parser.parse_args()

    print("🚀 Starting E2E Integration Tests")
    print("=" * 50)

    # Setup environment
    setup_environment()

    # Check LocalStack health
    if not args.skip_health_check:
        if not check_localstack_health():
            print("❌ LocalStack is not ready. Please start it with:")
            print(
                "   docker-compose -f tests/integrations/docker-compose.e2e.yml up -d"
            )
            return 1

    # Run tests
    exit_code = run_pytest_command(args.test_path, args.pytest_args)

    if exit_code == 0:
        print("\n✅ All tests passed!")
    else:
        print(f"\n❌ Tests failed with exit code: {exit_code}")

    return exit_code


if __name__ == "__main__":
    sys.exit(main())
