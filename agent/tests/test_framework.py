# Load environment variables first
import dotenv

dotenv.load_dotenv()

import asyncio
import json
import logging
import os
import sys
from dataclasses import asdict, dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Optional

# Add the parent directory to the Python path so we can import vocab_processor
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from rich.columns import Columns

# Add Rich for colored output and better formatting
from rich.console import Console
from rich.panel import Panel
from rich.syntax import Syntax
from rich.table import Table
from rich.text import Text
from rich.tree import Tree

# Initialize Rich console
console = Console()

from vocab_processor.agent import graph
from vocab_processor.constants import Language

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@dataclass
class TestCase:
    """Represents a single test case with input and expected output."""

    test_id: str
    description: str
    input_data: dict[str, Any]
    expected_output: Optional[dict[str, Any]] = None
    tags: Optional[list[str]] = None
    created_at: Optional[str] = None
    updated_at: Optional[str] = None


@dataclass
class TestResult:
    """Represents the result of running a test case."""

    test_id: str
    passed: bool
    actual_output: dict[str, Any]
    expected_output: Optional[dict[str, Any]] = None
    differences: Optional[dict[str, Any]] = None
    execution_time: Optional[float] = None
    error: Optional[str] = None
    timestamp: Optional[str] = None


class LangGraphTestFramework:
    """Test framework for LangGraph vocabulary processing workflow."""

    def __init__(self, test_data_dir: str = "test_data"):
        # Make test_data_dir relative to the tests directory
        tests_dir = Path(__file__).parent
        self.test_data_dir = tests_dir / test_data_dir
        self.test_data_dir.mkdir(exist_ok=True)

        # Create subdirectories
        (self.test_data_dir / "test_cases").mkdir(exist_ok=True)
        (self.test_data_dir / "ground_truth").mkdir(exist_ok=True)
        (self.test_data_dir / "results").mkdir(exist_ok=True)

        self.test_cases: list[TestCase] = []
        self.ground_truth: dict[str, dict[str, Any]] = {}

        self.excluded_attributes = {
            "parallel_tasks_complete",
            "processing_complete",
            "parallel_tasks_to_execute",
            "completed_parallel_tasks",
            "media",
            "media_reused",
            "pronunciations",
        }

    def _filter_excluded_attributes(self, data: dict[str, Any]) -> dict[str, Any]:
        """Filter out excluded attributes from the data dictionary.

        Args:
            data: Dictionary containing vocabulary processing results

        Returns:
            Dictionary with excluded attributes removed
        """
        if not isinstance(data, dict):
            return data

        filtered_data = {}
        for key, value in data.items():
            if key not in self.excluded_attributes:
                filtered_data[key] = value
        return filtered_data

    def add_excluded_attributes(self, *attributes: str) -> None:
        """Add additional attributes to exclude from comparison and storage.

        Args:
            *attributes: Attribute names to exclude
        """
        self.excluded_attributes.update(attributes)

    def remove_excluded_attributes(self, *attributes: str) -> None:
        """Remove attributes from the exclusion list.

        Args:
            *attributes: Attribute names to stop excluding
        """
        for attr in attributes:
            self.excluded_attributes.discard(attr)

    def get_excluded_attributes(self) -> set[str]:
        """Get the current set of excluded attributes.

        Returns:
            Set of attribute names that are excluded
        """
        return self.excluded_attributes.copy()

    def add_test_case(
        self,
        test_id: str,
        description: str,
        source_word: str,
        target_language: Language,
        tags: Optional[list[str]] = None,
    ) -> TestCase:
        """Add a new test case to the test suite."""
        test_case = TestCase(
            test_id=test_id,
            description=description,
            input_data={
                "source_word": source_word,
                "target_language": (
                    target_language.value
                    if isinstance(target_language, Language)
                    else target_language
                ),
            },
            tags=tags or [],
            created_at=datetime.now().isoformat(),
        )
        self.test_cases.append(test_case)
        return test_case

    def load_test_cases_from_file(self, file_path: str) -> None:
        """Load test cases from a JSON file."""
        try:
            with open(file_path, "r") as f:
                data = json.load(f)
                for item in data:
                    test_case = TestCase(**item)
                    self.test_cases.append(test_case)
            logger.info(f"Loaded {len(data)} test cases from {file_path}")
        except Exception as e:
            logger.error(f"Error loading test cases from {file_path}: {e}")

    def save_test_cases(self, file_path: Optional[str] = None) -> None:
        """Save test cases to a JSON file."""
        if not file_path:
            file_path = self.test_data_dir / "test_cases" / "test_cases.json"

        with open(file_path, "w") as f:
            json.dump([asdict(tc) for tc in self.test_cases], f, indent=2)
        logger.info(f"Saved {len(self.test_cases)} test cases to {file_path}")

    async def run_single_test(self, test_case: TestCase) -> TestResult:
        """Run a single test case through the graph."""
        start_time = asyncio.get_event_loop().time()

        try:
            # Run the graph with the test input
            result = await graph.ainvoke(test_case.input_data)

            # Convert result to dict if it's a Pydantic model
            if hasattr(result, "model_dump"):
                actual_output = result.model_dump()
            else:
                actual_output = dict(result)

            execution_time = asyncio.get_event_loop().time() - start_time

            # Check if we have expected output (ground truth)
            expected_output = test_case.expected_output
            passed = True
            differences = None

            if expected_output:
                differences = self._compare_outputs(actual_output, expected_output)
                passed = len(differences) == 0

            return TestResult(
                test_id=test_case.test_id,
                passed=passed,
                actual_output=actual_output,
                expected_output=expected_output,
                differences=differences,
                execution_time=execution_time,
                timestamp=datetime.now().isoformat(),
            )

        except Exception as e:
            execution_time = asyncio.get_event_loop().time() - start_time
            return TestResult(
                test_id=test_case.test_id,
                passed=False,
                actual_output={},
                expected_output=test_case.expected_output,
                execution_time=execution_time,
                error=str(e),
                timestamp=datetime.now().isoformat(),
            )

    async def build_ground_truth(
        self, test_cases: Optional[list[TestCase]] = None
    ) -> dict[str, TestResult]:
        """Build ground truth by running test cases and storing their outputs."""
        if test_cases is None:
            test_cases = self.test_cases

        results = {}

        for test_case in test_cases:
            logger.info(f"Building ground truth for test case: {test_case.test_id}")
            result = await self.run_single_test(test_case)

            if result.passed and not result.error:
                # Store as ground truth
                test_case.expected_output = result.actual_output
                test_case.updated_at = datetime.now().isoformat()
                results[test_case.test_id] = result
                logger.info(f"✓ Ground truth built for {test_case.test_id}")
            else:
                logger.error(
                    f"✗ Failed to build ground truth for {test_case.test_id}: {result.error}"
                )
                results[test_case.test_id] = result

        # Save ground truth
        self.save_ground_truth()
        return results

    def save_ground_truth(self, file_path: Optional[str] = None) -> None:
        """Save ground truth data to file."""
        if not file_path:
            file_path = self.test_data_dir / "ground_truth" / "ground_truth.json"

        ground_truth_data = {}
        for tc in self.test_cases:
            if tc.expected_output is not None:
                # Convert to serializable format
                serializable_output = self._make_serializable(tc.expected_output)
                # Filter out excluded attributes
                filtered_output = self._filter_excluded_attributes(serializable_output)
                ground_truth_data[tc.test_id] = filtered_output

        with open(file_path, "w") as f:
            json.dump(ground_truth_data, f, indent=2)
        logger.info(f"Saved ground truth for {len(ground_truth_data)} test cases")

    def load_ground_truth(self, file_path: Optional[str] = None) -> None:
        """Load ground truth data from file."""
        if not file_path:
            file_path = self.test_data_dir / "ground_truth" / "ground_truth.json"

        try:
            with open(file_path, "r") as f:
                ground_truth_data = json.load(f)

            # Update test cases with ground truth
            for test_case in self.test_cases:
                if test_case.test_id in ground_truth_data:
                    test_case.expected_output = ground_truth_data[test_case.test_id]

            logger.info(f"Loaded ground truth for {len(ground_truth_data)} test cases")
        except Exception as e:
            logger.error(f"Error loading ground truth: {e}")

    async def run_test_suite(
        self, test_cases: Optional[list[TestCase]] = None
    ) -> list[TestResult]:
        """Run the full test suite and return results."""
        if test_cases is None:
            test_cases = self.test_cases

        results = []

        for test_case in test_cases:
            logger.info(f"Running test case: {test_case.test_id}")
            result = await self.run_single_test(test_case)
            results.append(result)

            status = "✓ PASS" if result.passed else "✗ FAIL"
            logger.info(f"{status} - {test_case.test_id}")

            if result.error:
                logger.error(f"Error: {result.error}")

        # Save results
        self.save_test_results(results)
        return results

    def save_test_results(
        self, results: list[TestResult], file_path: Optional[str] = None
    ) -> None:
        """Save test results to file."""
        if not file_path:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            file_path = (
                self.test_data_dir / "results" / f"test_results_{timestamp}.json"
            )

        # Convert results to serializable format
        serializable_results = []
        for result in results:
            result_dict = asdict(result)
            # Make sure all nested objects are serializable
            result_dict["actual_output"] = self._make_serializable(
                result_dict["actual_output"]
            )
            if result_dict["expected_output"]:
                result_dict["expected_output"] = self._make_serializable(
                    result_dict["expected_output"]
                )

            # Filter out excluded attributes from both outputs
            result_dict["actual_output"] = self._filter_excluded_attributes(
                result_dict["actual_output"]
            )
            if result_dict["expected_output"]:
                result_dict["expected_output"] = self._filter_excluded_attributes(
                    result_dict["expected_output"]
                )

            serializable_results.append(result_dict)

        with open(file_path, "w") as f:
            json.dump(serializable_results, f, indent=2)
        logger.info(f"Saved test results to {file_path}")

    def _compare_outputs(
        self, actual: dict[str, Any], expected: dict[str, Any]
    ) -> dict[str, Any]:
        """Compare actual output with expected output and return differences."""
        differences = {}

        # Serialize both outputs to make them comparable
        serialized_actual = self._make_serializable(actual)
        serialized_expected = self._make_serializable(expected)

        # Filter out excluded attributes from both outputs
        filtered_actual = self._filter_excluded_attributes(serialized_actual)
        filtered_expected = self._filter_excluded_attributes(serialized_expected)

        # Check for missing keys in actual
        for key in filtered_expected:
            if key not in filtered_actual:
                differences[f"missing_{key}"] = (
                    f"Expected key '{key}' not found in actual output"
                )

        # Check for differing values
        for key in filtered_expected:
            if (
                key in filtered_actual
                and filtered_actual[key] != filtered_expected[key]
            ):
                differences[f"diff_{key}"] = {
                    "expected": filtered_expected[key],
                    "actual": filtered_actual[key],
                }

        # Check for extra keys in actual
        for key in filtered_actual:
            if key not in filtered_expected:
                differences[f"extra_{key}"] = (
                    f"Unexpected key '{key}' found in actual output"
                )

        return differences

    def _format_value_for_diff(self, value: Any, indent: int = 0) -> str:
        """Format a value for diff display with proper indentation."""
        indent_str = "  " * indent

        if isinstance(value, dict):
            if not value:
                return "{}"
            lines = ["{"]
            for k, v in value.items():
                formatted_value = self._format_value_for_diff(v, indent + 1)
                lines.append(f"{indent_str}  {repr(k)}: {formatted_value},")
            lines.append(f"{indent_str}}}")
            return "\n".join(lines)
        elif isinstance(value, list):
            if not value:
                return "[]"
            lines = ["["]
            for item in value:
                formatted_item = self._format_value_for_diff(item, indent + 1)
                lines.append(f"{indent_str}  {formatted_item},")
            lines.append(f"{indent_str}]")
            return "\n".join(lines)
        else:
            return repr(value)

    def generate_colored_diff(
        self, actual: dict[str, Any], expected: dict[str, Any]
    ) -> str:
        """Generate a colored diff between actual and expected outputs using Rich."""
        # Create a string buffer to capture console output
        from io import StringIO

        diff_console = Console(file=StringIO(), width=120)

        # Header
        diff_console.print(Panel("DETAILED DIFF", style="cyan bold", width=60))

        # Get all keys from both dictionaries (inputs are already filtered)
        all_keys = set(actual.keys()) | set(expected.keys())

        for key in sorted(all_keys):
            actual_value = actual.get(key, "<MISSING>")
            expected_value = expected.get(key, "<MISSING>")

            if key not in expected:
                # Extra key in actual
                diff_console.print(f"\n[red bold]+ EXTRA KEY: {key}[/red bold]")
                formatted_value = self._format_value_for_diff(actual_value)
                syntax = Syntax(
                    formatted_value, "json", theme="monokai", line_numbers=False
                )
                diff_console.print(Panel(syntax, border_style="red", title="Added"))

            elif key not in actual:
                # Missing key in actual
                diff_console.print(f"\n[red bold]- MISSING KEY: {key}[/red bold]")
                formatted_value = self._format_value_for_diff(expected_value)
                syntax = Syntax(
                    formatted_value, "json", theme="monokai", line_numbers=False
                )
                diff_console.print(Panel(syntax, border_style="red", title="Missing"))

            elif actual_value != expected_value:
                # Different values
                diff_console.print(f"\n[yellow bold]~ CHANGED: {key}[/yellow bold]")

                # Show expected vs actual in columns
                formatted_expected = self._format_value_for_diff(expected_value)
                formatted_actual = self._format_value_for_diff(actual_value)

                expected_syntax = Syntax(
                    formatted_expected, "json", theme="monokai", line_numbers=False
                )
                actual_syntax = Syntax(
                    formatted_actual, "json", theme="monokai", line_numbers=False
                )

                expected_panel = Panel(
                    expected_syntax, border_style="red", title="Expected"
                )
                actual_panel = Panel(
                    actual_syntax, border_style="green", title="Actual"
                )

                diff_console.print(Columns([expected_panel, actual_panel]))
            else:
                # Values match - show in green
                diff_console.print(f"\n[green bold]✓ MATCH: {key}[/green bold]")

        return diff_console.file.getvalue()

    def generate_test_report(self, results: list[TestResult]) -> str:
        """Generate a human-readable test report using Rich."""
        from io import StringIO

        report_console = Console(file=StringIO(), width=100)

        total_tests = len(results)
        passed_tests = sum(1 for r in results if r.passed)
        failed_tests = total_tests - passed_tests

        # Header
        report_console.print(
            Panel("[cyan bold]LangGraph Test Report[/cyan bold]", width=50)
        )
        report_console.print(
            f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
        )
        report_console.print()

        # Summary table
        table = Table(title="Summary")
        table.add_column("Metric", style="cyan")
        table.add_column("Value", style="bold")

        table.add_row("Total Tests", str(total_tests))
        table.add_row("Passed", f"[green]{passed_tests}[/green]")
        table.add_row("Failed", f"[red]{failed_tests}[/red]")
        table.add_row("Success Rate", f"{(passed_tests/total_tests)*100:.1f}%")

        report_console.print(table)
        report_console.print()

        if failed_tests > 0:
            report_console.print("[red bold]Failed Tests:[/red bold]")
            for result in results:
                if not result.passed:
                    report_console.print(
                        f"  [red]✗ {result.test_id}: {result.error or 'Output mismatch'}[/red]"
                    )
                    if result.differences:
                        for diff_key, diff_value in result.differences.items():
                            report_console.print(
                                f"    [yellow]{diff_key}: {diff_value}[/yellow]"
                            )

        return report_console.file.getvalue()

    def generate_colored_test_report(self, results: list[TestResult]) -> str:
        """Generate a colored test report with detailed diffs for regression testing using Rich."""
        from io import StringIO

        report_console = Console(file=StringIO(), width=120)

        total_tests = len(results)
        passed_tests = sum(1 for r in results if r.passed)
        failed_tests = total_tests - passed_tests

        # Header
        report_console.print(
            Panel("[cyan bold]LANGGRAPH REGRESSION TEST REPORT[/cyan bold]", width=80)
        )
        report_console.print(
            f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
        )
        report_console.print()

        # Summary table
        table = Table(title="[cyan bold]SUMMARY[/cyan bold]")
        table.add_column("Metric", style="cyan")
        table.add_column("Value", style="bold")

        table.add_row("Total Tests", str(total_tests))
        table.add_row("Passed", f"[green]{passed_tests}[/green]")
        table.add_row("Failed", f"[red]{failed_tests}[/red]")

        if total_tests > 0:
            success_rate = (passed_tests / total_tests) * 100
            color = (
                "green"
                if success_rate >= 90
                else "yellow" if success_rate >= 70 else "red"
            )
            table.add_row("Success Rate", f"[{color}]{success_rate:.1f}%[/{color}]")

        report_console.print(table)
        report_console.print()

        # Detailed results
        if passed_tests > 0:
            report_console.print("[green bold]PASSED TESTS:[/green bold]")
            for result in results:
                if result.passed:
                    exec_time = (
                        f" ({result.execution_time:.2f}s)"
                        if result.execution_time
                        else ""
                    )
                    report_console.print(
                        f"  [green]✓[/green] {result.test_id}{exec_time}"
                    )
            report_console.print()

        if failed_tests > 0:
            report_console.print("[red bold]FAILED TESTS:[/red bold]")
            for result in results:
                if not result.passed:
                    exec_time = (
                        f" ({result.execution_time:.2f}s)"
                        if result.execution_time
                        else ""
                    )
                    report_console.print(f"  [red]✗[/red] {result.test_id}{exec_time}")

                    if result.error:
                        report_console.print(f"    [red]Error: {result.error}[/red]")

                    # Show colored diff if we have both expected and actual outputs
                    if result.expected_output and result.actual_output:
                        # Filter out excluded attributes before displaying diff
                        filtered_actual = self._filter_excluded_attributes(
                            result.actual_output
                        )
                        filtered_expected = self._filter_excluded_attributes(
                            result.expected_output
                        )

                        # Generate diff content as string instead of printing to console
                        report_console.print(
                            Panel("DETAILED DIFF", style="cyan bold", width=60)
                        )

                        # Get all keys from both dictionaries (inputs are already filtered)
                        all_keys = set(filtered_actual.keys()) | set(
                            filtered_expected.keys()
                        )

                        for key in sorted(all_keys):
                            actual_value = filtered_actual.get(key, "<MISSING>")
                            expected_value = filtered_expected.get(key, "<MISSING>")

                            if key not in filtered_expected:
                                # Extra key in actual
                                report_console.print(
                                    f"\n[red bold]+ EXTRA KEY: {key}[/red bold]"
                                )
                                formatted_value = self._format_value_for_diff(
                                    actual_value
                                )
                                report_console.print(
                                    Panel(
                                        formatted_value,
                                        border_style="red",
                                        title="Added",
                                    )
                                )

                            elif key not in filtered_actual:
                                # Missing key in actual
                                report_console.print(
                                    f"\n[red bold]- MISSING KEY: {key}[/red bold]"
                                )
                                formatted_value = self._format_value_for_diff(
                                    expected_value
                                )
                                report_console.print(
                                    Panel(
                                        formatted_value,
                                        border_style="red",
                                        title="Missing",
                                    )
                                )

                            elif actual_value != expected_value:
                                # Different values
                                report_console.print(
                                    f"\n[yellow bold]~ CHANGED: {key}[/yellow bold]"
                                )

                                # Show expected vs actual in columns with plain text
                                formatted_expected = self._format_value_for_diff(
                                    expected_value
                                )
                                formatted_actual = self._format_value_for_diff(
                                    actual_value
                                )

                                expected_panel = Panel(
                                    formatted_expected,
                                    border_style="red",
                                    title="Expected",
                                )
                                actual_panel = Panel(
                                    formatted_actual,
                                    border_style="green",
                                    title="Actual",
                                )

                                report_console.print(
                                    Columns([expected_panel, actual_panel])
                                )
                            else:
                                # Values match - show in green
                                report_console.print(
                                    f"\n[green bold]✓ MATCH: {key}[/green bold]"
                                )

        return report_console.file.getvalue()

    def print_colored_diff(
        self, actual: dict[str, Any], expected: dict[str, Any]
    ) -> None:
        """Print a colored diff between actual and expected outputs directly to console."""
        # Print directly to console to preserve colors
        console.print(Panel("DETAILED DIFF", style="cyan bold", width=60))

        # Get all keys from both dictionaries (inputs are already filtered)
        all_keys = set(actual.keys()) | set(expected.keys())

        for key in sorted(all_keys):
            actual_value = actual.get(key, "<MISSING>")
            expected_value = expected.get(key, "<MISSING>")

            if key not in expected:
                # Extra key in actual
                console.print(f"\n[red bold]+ EXTRA KEY: {key}[/red bold]")
                formatted_value = self._format_value_for_diff(actual_value)
                # Use plain text instead of syntax highlighting
                console.print(Panel(formatted_value, border_style="red", title="Added"))

            elif key not in actual:
                # Missing key in actual
                console.print(f"\n[red bold]- MISSING KEY: {key}[/red bold]")
                formatted_value = self._format_value_for_diff(expected_value)
                # Use plain text instead of syntax highlighting
                console.print(
                    Panel(formatted_value, border_style="red", title="Missing")
                )

            elif actual_value != expected_value:
                # Different values
                console.print(f"\n[yellow bold]~ CHANGED: {key}[/yellow bold]")

                # Show expected vs actual in columns with plain text
                formatted_expected = self._format_value_for_diff(expected_value)
                formatted_actual = self._format_value_for_diff(actual_value)

                expected_panel = Panel(
                    formatted_expected, border_style="red", title="Expected"
                )
                actual_panel = Panel(
                    formatted_actual, border_style="green", title="Actual"
                )

                console.print(Columns([expected_panel, actual_panel]))
            else:
                # Values match - show in green
                console.print(f"\n[green bold]✓ MATCH: {key}[/green bold]")

    def print_colored_test_report(self, results: list[TestResult]) -> None:
        """Print a colored test report with detailed diffs for regression testing directly to console."""
        total_tests = len(results)
        passed_tests = sum(1 for r in results if r.passed)
        failed_tests = total_tests - passed_tests

        # Header
        console.print(
            Panel("[cyan bold]LANGGRAPH REGRESSION TEST REPORT[/cyan bold]", width=80)
        )
        console.print(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        console.print()

        # Summary table
        table = Table(title="[cyan bold]SUMMARY[/cyan bold]")
        table.add_column("Metric", style="cyan")
        table.add_column("Value", style="bold")

        table.add_row("Total Tests", str(total_tests))
        table.add_row("Passed", f"[green]{passed_tests}[/green]")
        table.add_row("Failed", f"[red]{failed_tests}[/red]")

        if total_tests > 0:
            success_rate = (passed_tests / total_tests) * 100
            color = (
                "green"
                if success_rate >= 90
                else "yellow" if success_rate >= 70 else "red"
            )
            table.add_row("Success Rate", f"[{color}]{success_rate:.1f}%[/{color}]")

        console.print(table)
        console.print()

        # Detailed results
        if passed_tests > 0:
            console.print("[green bold]PASSED TESTS:[/green bold]")
            for result in results:
                if result.passed:
                    exec_time = (
                        f" ({result.execution_time:.2f}s)"
                        if result.execution_time
                        else ""
                    )
                    console.print(f"  [green]✓[/green] {result.test_id}{exec_time}")
            console.print()

        if failed_tests > 0:
            console.print("[red bold]FAILED TESTS:[/red bold]")
            for result in results:
                if not result.passed:
                    exec_time = (
                        f" ({result.execution_time:.2f}s)"
                        if result.execution_time
                        else ""
                    )
                    console.print(f"  [red]✗[/red] {result.test_id}{exec_time}")

                    if result.error:
                        console.print(f"    [red]Error: {result.error}[/red]")

                    # Show colored diff if we have both expected and actual outputs
                    if result.expected_output and result.actual_output:
                        # Filter out excluded attributes before displaying diff
                        filtered_actual = self._filter_excluded_attributes(
                            result.actual_output
                        )
                        filtered_expected = self._filter_excluded_attributes(
                            result.expected_output
                        )
                        self.print_colored_diff(filtered_actual, filtered_expected)

                    console.print()

    def compare_test_results(
        self, test_id: str, actual_result: TestResult, expected_result: TestResult
    ) -> None:
        """Compare two test results and display a colored diff."""
        console.print(f"\n[cyan bold]COMPARISON FOR TEST: {test_id}[/cyan bold]")

        if actual_result.actual_output and expected_result.actual_output:
            # Filter out excluded attributes before displaying diff with direct printing
            filtered_actual = self._filter_excluded_attributes(
                actual_result.actual_output
            )
            filtered_expected = self._filter_excluded_attributes(
                expected_result.actual_output
            )
            self.print_colored_diff(filtered_actual, filtered_expected)
        else:
            console.print("[red]Cannot compare: Missing output data[/red]")

    def quick_diff_demo(self) -> None:
        """Demonstrate the colored diff functionality with sample data."""
        console.print("[cyan bold]COLORED DIFF DEMONSTRATION[/cyan bold]")

        # Sample data for demonstration
        expected = {
            "source_word": "Haus",
            "target_word": "casa",
            "validation_passed": True,
            "source_language": "German",
            "target_language": "Spanish",
            "synonyms": ["vivienda", "hogar", "residencia"],
            "overall_quality_score": 9.5,
            "examples": [
                {"original": "Das ist mein Haus.", "translation": "Esta es mi casa."},
                {"original": "Ich kaufe ein Haus.", "translation": "Compro una casa."},
            ],
        }

        actual = {
            "source_word": "Haus",
            "target_word": "hogar",  # Different translation
            "validation_passed": False,  # Different validation
            "source_language": "German",
            "target_language": "Spanish",
            "synonyms": ["casa", "vivienda"],  # Different synonyms
            "overall_quality_score": 7.2,  # Different score
            "examples": [
                {"original": "Das ist mein Haus.", "translation": "Este es mi hogar."},
                # Missing second example
            ],
            "extra_field": "This shouldn't be here",  # Extra field
        }

        console.print("\n[yellow]This is a demonstration of how diffs look:[/yellow]")
        # Use filtered outputs for demonstration with direct printing
        filtered_actual = self._filter_excluded_attributes(actual)
        filtered_expected = self._filter_excluded_attributes(expected)
        self.print_colored_diff(filtered_actual, filtered_expected)

    def _make_serializable(self, obj: Any, _seen: set = None) -> Any:
        """Convert objects to JSON serializable format with recursion protection."""
        if _seen is None:
            _seen = set()

        # Handle basic JSON-serializable types first
        if obj is None or isinstance(obj, (str, int, float, bool)):
            return obj

        # Check for circular references using object id
        obj_id = id(obj)
        if obj_id in _seen:
            return f"<circular reference to {type(obj).__name__}>"

        # Add to seen set for complex objects
        _seen.add(obj_id)

        try:
            # Handle Pydantic models first
            if hasattr(obj, "model_dump"):
                try:
                    result = obj.model_dump()
                    return self._make_serializable(result, _seen)
                except Exception as e:
                    # If model_dump fails, try dict conversion
                    logger.warning(f"model_dump failed for {type(obj).__name__}: {e}")
                    return {
                        k: self._make_serializable(v, _seen)
                        for k, v in obj.__dict__.items()
                        if not k.startswith("_")
                    }

            # Handle enums
            elif hasattr(obj, "value"):
                return obj.value

            # Handle dictionaries
            elif isinstance(obj, dict):
                return {k: self._make_serializable(v, _seen) for k, v in obj.items()}

            # Handle lists and tuples
            elif isinstance(obj, (list, tuple)):
                serialized_items = [
                    self._make_serializable(item, _seen) for item in obj
                ]
                return (
                    serialized_items
                    if isinstance(obj, list)
                    else tuple(serialized_items)
                )

            # Handle sets
            elif isinstance(obj, set):
                return [self._make_serializable(item, _seen) for item in obj]

            # Handle custom objects with __dict__
            elif hasattr(obj, "__dict__"):
                return {
                    k: self._make_serializable(v, _seen)
                    for k, v in obj.__dict__.items()
                    if not k.startswith("_")  # Skip private attributes
                }

            # For other types, convert to string
            else:
                return str(obj)

        except Exception as e:
            # If all else fails, return a safe string representation
            logger.warning(f"Serialization failed for {type(obj).__name__}: {e}")
            return f"<serialization error: {type(obj).__name__}>"
        finally:
            # Remove from seen set when done with this branch
            _seen.discard(obj_id)


# Example usage and predefined test cases
def create_sample_test_cases() -> list[TestCase]:
    """Create sample test cases for the vocabulary processing workflow."""
    return [
        TestCase(
            test_id="test_german_to_spanish",
            description="Test German word 'Haus' to Spanish translation",
            input_data={"source_word": "Haus", "target_language": "Spanish"},
            tags=["german", "spanish", "noun"],
        ),
        TestCase(
            test_id="test_english_to_french",
            description="Test English word 'house' to French translation",
            input_data={"source_word": "house", "target_language": "French"},
            tags=["english", "french", "noun"],
        ),
        TestCase(
            test_id="test_spanish_verb",
            description="Test Spanish verb 'comer' to English",
            input_data={"source_word": "comer", "target_language": "English"},
            tags=["spanish", "english", "verb"],
        ),
        TestCase(
            test_id="test_invalid_word",
            description="Test invalid word handling",
            input_data={"source_word": "xyz123invalid", "target_language": "English"},
            tags=["validation", "error_handling"],
        ),
    ]


async def main():
    """Example usage of the test framework."""
    # Initialize test framework
    test_framework = LangGraphTestFramework()

    # Create sample test cases
    sample_cases = create_sample_test_cases()
    test_framework.test_cases = sample_cases

    # Save test cases
    test_framework.save_test_cases()

    # Build ground truth (run tests and save outputs as expected results)
    print("Building ground truth...")
    ground_truth_results = await test_framework.build_ground_truth()

    # Run test suite (this would compare against the ground truth we just built)
    print("\nRunning test suite...")
    test_results = await test_framework.run_test_suite()

    # Generate and print report
    report = test_framework.generate_test_report(test_results)
    print(report)

    # Save report to file
    with open(test_framework.test_data_dir / "results" / "latest_report.txt", "w") as f:
        f.write(report)


if __name__ == "__main__":
    asyncio.run(main())
