#!/usr/bin/env python3
"""
Integration Test Runner for Lambda and WebSocket functionality

This script provides various ways to run integration tests for the vocab processor
Lambda and WebSocket handlers.

Usage:
    python run_integration_tests.py --help
    python run_integration_tests.py --all
    python run_integration_tests.py --lambda
    python run_integration_tests.py --websocket
    python run_integration_tests.py --scenario new_vocab
    python run_integration_tests.py --scenario existing_word
    python run_integration_tests.py --scenario invalid_word
    python run_integration_tests.py --pytest
"""

import argparse
import asyncio
import os
import sys
from typing import Any

import dotenv

dotenv.load_dotenv()

# Add the project root directory to the Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

# Import test setup to initialize AWS mocks
from test_setup import setup_aws_mocks

# Initialize AWS mocks
setup_aws_mocks()

from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from test_integration import (
    IntegrationTestFramework,
    TestScenarios,
    run_integration_tests,
)

console = Console()


async def run_lambda_tests(framework: IntegrationTestFramework) -> list[dict[str, Any]]:
    """Run all Lambda integration tests."""
    console.print("[cyan]Running Lambda Integration Tests...[/cyan]")

    results = []

    # Test scenarios
    scenarios = [
        ("New Vocab Request", TestScenarios.new_vocab_request),
        ("Existing Word Request", TestScenarios.existing_word_request),
        ("Invalid Word Request", TestScenarios.invalid_word_request),
        ("Processing Failure", TestScenarios.processing_failure_request),
    ]

    for scenario_name, scenario_func in scenarios:
        console.print(f"Testing: {scenario_name}...")
        scenario = scenario_func()

        try:
            # Run with mock result if provided
            mock_result = scenario.get("mock_graph_result")
            result = await framework.test_lambda_scenario(
                scenario["request"], mock_result
            )
            results.append(
                {
                    "scenario": scenario_name,
                    "result": result,
                    "expected_notifications": scenario.get(
                        "expected_notifications", []
                    ),
                }
            )

            # Verify expected notifications
            notification_types = [
                notif["data"]["type"] for notif in result.websocket_notifications
            ]
            for expected_notif in scenario.get("expected_notifications", []):
                if expected_notif in notification_types:
                    console.print(f"  ✓ {expected_notif} notification sent")
                else:
                    console.print(f"  ✗ {expected_notif} notification missing")

        except Exception as e:
            console.print(f"  [red]Error: {e}[/red]")
            results.append({"scenario": scenario_name, "result": None, "error": str(e)})

    return results


def run_websocket_tests(framework: IntegrationTestFramework) -> list[dict[str, Any]]:
    """Run all WebSocket integration tests."""
    console.print("[cyan]Running WebSocket Integration Tests...[/cyan]")

    results = []

    # Test scenarios
    scenarios = [
        ("WebSocket Connect", TestScenarios.websocket_connect_event),
        ("WebSocket Subscribe", TestScenarios.websocket_subscribe_event),
        ("WebSocket Disconnect", TestScenarios.websocket_disconnect_event),
    ]

    for scenario_name, scenario_func in scenarios:
        console.print(f"Testing: {scenario_name}...")

        try:
            event = scenario_func()
            result = framework.test_websocket_scenario(event)
            results.append(
                {"scenario": scenario_name, "result": result, "expected_status": 200}
            )

            # Check status
            if result.response.get("statusCode") == 200:
                console.print(f"  ✓ Status: {result.response['statusCode']}")
            else:
                console.print(f"  ✗ Status: {result.response['statusCode']}")

        except Exception as e:
            console.print(f"  [red]Error: {e}[/red]")
            results.append({"scenario": scenario_name, "result": None, "error": str(e)})

    return results


async def run_specific_scenario(
    framework: IntegrationTestFramework, scenario_name: str
):
    """Run a specific test scenario."""
    console.print(f"[cyan]Running Specific Scenario: {scenario_name}[/cyan]")

    scenario_map = {
        "new_vocab": TestScenarios.new_vocab_request,
        "existing_word": TestScenarios.existing_word_request,
        "invalid_word": TestScenarios.invalid_word_request,
        "processing_failure": TestScenarios.processing_failure_request,
        "websocket_connect": TestScenarios.websocket_connect_event,
        "websocket_subscribe": TestScenarios.websocket_subscribe_event,
        "websocket_disconnect": TestScenarios.websocket_disconnect_event,
    }

    if scenario_name not in scenario_map:
        console.print(f"[red]Unknown scenario: {scenario_name}[/red]")
        console.print("Available scenarios:")
        for name in scenario_map.keys():
            console.print(f"  - {name}")
        return

    scenario_func = scenario_map[scenario_name]

    if scenario_name.startswith("websocket_"):
        # WebSocket test
        event = scenario_func()
        result = framework.test_websocket_scenario(event)

        console.print(f"Connection ID: {result.connection_id}")
        console.print(f"Action: {result.action}")
        console.print(f"Response: {result.response}")
        if result.error:
            console.print(f"[red]Error: {result.error}[/red]")
    else:
        # Lambda test
        scenario = scenario_func()
        mock_result = scenario.get("mock_graph_result")
        result = await framework.test_lambda_scenario(scenario["request"], mock_result)

        console.print(
            f"Request: {scenario['request'].source_word} -> {scenario['request'].target_language}"
        )
        console.print(f"Execution Time: {result.execution_time:.2f}s")
        console.print(f"Response: {result.response}")
        console.print(f"WebSocket Notifications: {len(result.websocket_notifications)}")
        console.print(f"DDB Operations: {len(result.ddb_operations)}")

        if result.error:
            console.print(f"[red]Error: {result.error}[/red]")

        # Show notifications
        if result.websocket_notifications:
            console.print("\nWebSocket Notifications:")
            for notif in result.websocket_notifications:
                console.print(f"  - {notif['data']['type']}: {notif['connection_id']}")


def run_pytest_tests():
    """Run tests using pytest."""
    console.print("[cyan]Running Tests with pytest...[/cyan]")

    import subprocess

    # Run pytest with specific test files
    test_files = [
        "test_integration_scenarios.py",
        # Add more test files as needed
    ]

    for test_file in test_files:
        if os.path.exists(test_file):
            console.print(f"Running {test_file}...")
            result = subprocess.run(
                [sys.executable, "-m", "pytest", test_file, "-v", "--tb=short"],
                capture_output=True,
                text=True,
            )

            if result.returncode == 0:
                console.print("[green]✓ Tests passed[/green]")
            else:
                console.print("[red]✗ Tests failed[/red]")
                console.print(result.stdout)
                console.print(result.stderr)
        else:
            console.print(f"[yellow]Test file not found: {test_file}[/yellow]")


def print_test_summary(
    lambda_results: list[dict[str, Any]] = None,
    websocket_results: list[dict[str, Any]] = None,
):
    """Print a summary of test results."""
    console.print(Panel("TEST SUMMARY", style="cyan bold"))

    if lambda_results:
        console.print("\n[bold]Lambda Tests:[/bold]")
        table = Table()
        table.add_column("Scenario", style="cyan")
        table.add_column("Status", style="bold")
        table.add_column("Execution Time", style="yellow")
        table.add_column("Notifications", style="blue")

        for test in lambda_results:
            if test.get("result"):
                status = (
                    "[green]✓ PASS[/green]"
                    if not test["result"].error
                    else "[red]✗ FAIL[/red]"
                )
                exec_time = f"{test['result'].execution_time:.2f}s"
                notifications = len(test["result"].websocket_notifications)
            else:
                status = "[red]✗ ERROR[/red]"
                exec_time = "N/A"
                notifications = 0

            table.add_row(test["scenario"], status, exec_time, str(notifications))

        console.print(table)

    if websocket_results:
        console.print("\n[bold]WebSocket Tests:[/bold]")
        table = Table()
        table.add_column("Scenario", style="cyan")
        table.add_column("Status", style="bold")
        table.add_column("Response Code", style="yellow")

        for test in websocket_results:
            if test.get("result"):
                status = (
                    "[green]✓ PASS[/green]"
                    if not test["result"].error
                    else "[red]✗ FAIL[/red]"
                )
                response_code = test["result"].response.get("statusCode", "N/A")
            else:
                status = "[red]✗ ERROR[/red]"
                response_code = "N/A"

            table.add_row(test["scenario"], status, str(response_code))

        console.print(table)


async def main():
    """Main test runner."""
    parser = argparse.ArgumentParser(
        description="Run integration tests for Lambda and WebSocket"
    )
    parser.add_argument("--all", action="store_true", help="Run all tests")
    parser.add_argument("--lambda", action="store_true", help="Run Lambda tests only")
    parser.add_argument(
        "--websocket", action="store_true", help="Run WebSocket tests only"
    )
    parser.add_argument("--scenario", type=str, help="Run specific scenario")
    parser.add_argument("--pytest", action="store_true", help="Run tests with pytest")
    parser.add_argument("--verbose", "-v", action="store_true", help="Verbose output")

    args = parser.parse_args()

    # Create framework
    framework = IntegrationTestFramework()

    lambda_results = None
    websocket_results = None

    if args.pytest:
        run_pytest_tests()
        return

    if args.scenario:
        await run_specific_scenario(framework, args.scenario)
        return

    if args.all or getattr(args, "lambda"):
        lambda_results = await run_lambda_tests(framework)

    if args.all or args.websocket:
        websocket_results = run_websocket_tests(framework)

    if not any(
        [args.all, getattr(args, "lambda"), args.websocket, args.scenario, args.pytest]
    ):
        # Default: run the main integration test suite
        console.print("[cyan]Running Default Integration Test Suite...[/cyan]")
        await run_integration_tests()
        return

    # Print summary
    print_test_summary(lambda_results, websocket_results)


if __name__ == "__main__":
    asyncio.run(main())
