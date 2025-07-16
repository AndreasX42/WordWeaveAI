# Load environment variables first
import dotenv

dotenv.load_dotenv()

import argparse
import asyncio
import os
import sys
from pathlib import Path

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

from rich.console import Console
from test_definitions import TEST_CASES
from test_framework import LangGraphTestFramework, TestCase

# Initialize Rich console
console = Console()


def main():
    """Main function to run the test framework."""
    parser = argparse.ArgumentParser(description="LangGraph Test Framework Runner")
    parser.add_argument(
        "command",
        choices=["build", "regression"],
        help="Command to execute: 'build' to create ground truth, 'regression' to run tests against ground truth.",
    )
    parser.add_argument(
        "--tags",
        nargs="+",
        help="Filter test cases by tags. Only tests with ALL specified tags will be run.",
    )
    parser.add_argument(
        "--test-id",
        dest="test_id",
        help="Run a single test by its ID (e.g., 'Ephemeral_English_to_Spanish').",
    )

    args = parser.parse_args()

    # Convert test case dicts to TestCase objects
    test_cases = [
        TestCase.from_dict(tc)
        for tc in TEST_CASES
        if not (
            args.test_id
            and TestCase.from_dict(tc).test_id.lower() != args.test_id.lower()
        )
        and not (
            args.tags
            and not all(tag in (TestCase.from_dict(tc).tags or []) for tag in args.tags)
        )
    ]

    if not test_cases:
        console.print(
            "[bold yellow]No test cases found matching the criteria.[/bold yellow]"
        )
        return

    # Define the directory for test data relative to this script's location
    tests_dir = Path(__file__).parent
    test_data_dir = tests_dir / "test_data"

    framework = LangGraphTestFramework(test_data_dir=str(test_data_dir))

    if args.command == "build":
        console.print(
            f"[bold cyan]Building ground truth for {len(test_cases)} test case(s)...[/bold cyan]"
        )
        asyncio.run(framework.build_ground_truth(test_cases))
        console.print("[bold green]Ground truth build complete.[/bold green]")

    elif args.command == "regression":
        console.print(
            f"[bold cyan]Running regression tests for {len(test_cases)} test case(s)...[/bold cyan]"
        )
        # Load existing ground truth for comparison
        framework.load_ground_truth(test_cases)

        results = asyncio.run(framework.run_test_suite(test_cases))

        # Print the detailed, colored report to the console
        framework.print_colored_test_report(results)


if __name__ == "__main__":
    main()
