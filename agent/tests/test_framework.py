# Load environment variables first
import dotenv

dotenv.load_dotenv()

import asyncio
import json
import logging
import os
import sys
from dataclasses import asdict, dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Optional

# Add the parent directory to the Python path so we can import vocab_processor
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from rich.columns import Columns

# Add Rich for colored output and better formatting
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

# Initialize Rich console
console = Console()

from tests.test_definitions import TestCaseDict
from vocab_processor.agent import graph

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def _generate_test_id(
    source_word: str, target_language: str, source_language: Optional[str] = None
) -> str:
    """Generate a unique ID for a test case."""
    # Replace spaces and special characters with underscores for safe test IDs
    import re

    safe_source_word = re.sub(r"[^a-zA-Z0-9]", "_", source_word)
    # Remove multiple consecutive underscores
    safe_source_word = re.sub(r"_+", "_", safe_source_word)
    # Remove leading/trailing underscores
    safe_source_word = safe_source_word.strip("_")

    if source_language:
        return f"{safe_source_word}_{source_language}_to_{target_language}"
    return f"{safe_source_word}_to_{target_language}"


@dataclass
class TestCase:
    """Represents a single test case with input and expected output."""

    source_word: str
    target_language: str
    source_language: Optional[str] = None
    description: Optional[str] = None
    tags: Optional[list[str]] = None
    test_id: str = field(init=False)
    expected_output: Optional[dict[str, Any]] = None
    expected_execution_time: Optional[float] = None
    expected_token_usage: Optional[dict[str, Any]] = None

    def __post_init__(self):
        self.test_id = _generate_test_id(
            self.source_word, self.target_language, self.source_language
        )

    @classmethod
    def from_dict(cls, data: TestCaseDict) -> "TestCase":
        return cls(**data)

    @property
    def input_data(self) -> dict[str, Any]:
        """Get the input data for the graph invocation."""
        return {
            "source_word": self.source_word,
            "target_language": self.target_language,
            "source_language": self.source_language,
        }


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
    timestamp: Optional[str] = field(default_factory=lambda: datetime.now().isoformat())
    token_usage: Optional[dict[str, Any]] = None


class LangGraphTestFramework:
    """Test framework for LangGraph vocabulary processing workflow."""

    def __init__(self, test_data_dir: str = "test_data"):
        # Make test_data_dir relative to the tests directory
        tests_dir = Path(__file__).parent
        self.test_data_dir = tests_dir / test_data_dir
        self.ground_truth_file = self.test_data_dir / "ground_truth.json"

        # Create directories
        self.test_data_dir.mkdir(exist_ok=True)
        (self.test_data_dir / "results").mkdir(exist_ok=True)

        # Attributes to exclude from comparison to reduce noise in results
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
        """Filter out excluded attributes from the data dictionary."""
        if not isinstance(data, dict):
            return data
        return {k: v for k, v in data.items() if k not in self.excluded_attributes}

    def _summarize_token_usage(self, token_usage: dict) -> dict:
        """Return only the summary fields from token usage."""
        if not token_usage:
            return None
        return {
            "test_id": token_usage.get("test_id"),
            "total_execution_time": token_usage.get("total_execution_time"),
            "total_input_tokens": token_usage.get("total_input_tokens"),
            "total_output_tokens": token_usage.get("total_output_tokens"),
            "total_tokens": token_usage.get("total_tokens"),
        }

    async def run_single_test(self, test_case: TestCase) -> TestResult:
        """Run a single test case through the graph."""
        console.print(f"[yellow]Starting test: {test_case.test_id}[/yellow]")
        start_time = asyncio.get_event_loop().time()

        # Clear token tracker before starting new test
        try:
            from vocab_processor.utils.token_tracker import get_token_tracker

            tracker = get_token_tracker()
            tracker.clear()  # Clear any previous test data
            tracker.start_test(test_case.test_id)
        except Exception as e:
            logger.error(f"Failed to start token tracking for {test_case.test_id}: {e}")
            tracker = None

        try:
            result = await graph.ainvoke(test_case.input_data)
            actual_output = self._make_serializable(result)
            execution_time = asyncio.get_event_loop().time() - start_time

            # Capture token usage
            token_usage = None
            if tracker:
                test_usage = tracker.end_test(execution_time)
                if test_usage:
                    token_usage = self._summarize_token_usage(test_usage.to_dict())

            differences = None
            passed = True
            if test_case.expected_output:
                # Use regression-focused comparison
                differences = self._compare_regression_metrics(
                    actual_output,
                    test_case.expected_output,
                    token_usage,
                    test_case.expected_token_usage,
                )
                passed = not differences

            console.print(
                f"[green]Completed test: {test_case.test_id} ({execution_time:.2f}s)[/green]"
            )
            return TestResult(
                test_id=test_case.test_id,
                passed=passed,
                actual_output=actual_output,
                expected_output=test_case.expected_output,
                differences=differences,
                execution_time=execution_time,
                token_usage=token_usage,
            )

        except Exception as e:
            logger.exception(f"Exception during test case {test_case.test_id}")
            execution_time = asyncio.get_event_loop().time() - start_time

            # Capture token usage even on error
            token_usage = None
            if tracker:
                test_usage = tracker.end_test(execution_time)
                if test_usage:
                    token_usage = self._summarize_token_usage(test_usage.to_dict())

            differences = None
            passed = False
            if test_case.expected_output:
                # Use regression-focused comparison even on error
                differences = self._compare_regression_metrics(
                    {},
                    test_case.expected_output,
                    token_usage,
                    test_case.expected_token_usage,
                )

            console.print(
                f"[red]Failed test: {test_case.test_id} ({execution_time:.2f}s) - {str(e)}[/red]"
            )
            return TestResult(
                test_id=test_case.test_id,
                passed=passed,
                actual_output={},
                expected_output=test_case.expected_output,
                execution_time=execution_time,
                error=str(e),
                token_usage=token_usage,
                differences=differences,
            )

    async def build_ground_truth(self, test_cases: list[TestCase]) -> None:
        """Build ground truth by running test cases sequentially and storing their outputs."""
        ground_truth_data = {}
        console.print(
            f"Building ground truth for {len(test_cases)} tests sequentially..."
        )

        for i, tc in enumerate(test_cases, 1):
            console.print(
                f"[cyan]Processing test {i}/{len(test_cases)}: {tc.test_id}[/cyan]"
            )
            try:
                result = await self.run_single_test(tc)
                if not result.error:
                    filtered_output = self._filter_excluded_attributes(
                        result.actual_output
                    )
                    # Only keep output and token_usage (no top-level execution_time)
                    ground_truth_entry = {
                        "output": filtered_output,
                    }
                    if result.token_usage:
                        ground_truth_entry["token_usage"] = self._summarize_token_usage(
                            result.token_usage
                        )
                    ground_truth_data[result.test_id] = ground_truth_entry
                    console.print(
                        f"[green]✓ Ground truth built for {result.test_id}[/green]"
                    )
                    if result.execution_time:
                        console.print(
                            f"   Execution time: {result.execution_time:.2f}s"
                        )
                    if result.token_usage:
                        console.print(
                            f"   Tokens: {result.token_usage.get('total_tokens', 'N/A')}"
                        )
                else:
                    console.print(
                        f"[red]✗ Failed to build ground truth for {result.test_id}: {result.error}[/red]"
                    )
            except Exception as e:
                console.print(
                    f"[red]Test case {tc.test_id} failed with exception: {e}[/red]"
                )

        # Save ground truth
        self.save_ground_truth(ground_truth_data)

    def save_ground_truth(self, ground_truth_data: dict[str, Any]) -> None:
        """Save ground truth data to file."""
        with open(self.ground_truth_file, "w") as f:
            json.dump(ground_truth_data, f, indent=2)
        logger.info(
            f"Saved ground truth for {len(ground_truth_data)} test cases to {self.ground_truth_file}"
        )

    def load_ground_truth(self, test_cases: list[TestCase]) -> None:
        """Load ground truth data and attach it to the test cases."""
        try:
            with open(self.ground_truth_file, "r") as f:
                ground_truth_data = json.load(f)

            for tc in test_cases:
                if tc.test_id in ground_truth_data:
                    entry = ground_truth_data[tc.test_id]

                    # Handle both old format (direct output) and new format (with metadata)
                    if isinstance(entry, dict) and "output" in entry:
                        # New format with metadata
                        tc.expected_output = entry["output"]
                        # Store execution time and token usage for comparison
                        tc.expected_execution_time = entry.get("execution_time")
                        tc.expected_token_usage = entry.get("token_usage")
                    else:
                        # Old format - just the output
                        tc.expected_output = entry

            logger.info(f"Loaded ground truth for {len(ground_truth_data)} test cases.")
        except FileNotFoundError:
            logger.warning(
                "Ground truth file not found. Run with 'build' command to create it."
            )
        except Exception as e:
            logger.error(f"Error loading ground truth: {e}")

    async def run_test_suite(self, test_cases: list[TestCase]) -> list[TestResult]:
        """Run the full test suite sequentially and return results."""
        console.print(
            f"Running regression tests for {len(test_cases)} test cases sequentially..."
        )

        results = []
        for tc in test_cases:
            result = await self.run_single_test(tc)
            results.append(result)

            # Print status immediately after each test
            status = "[green]✓ PASS[/green]" if result.passed else "[red]✗ FAIL[/red]"
            console.print(f"{status} - {result.test_id}")

        self.save_test_results(results)
        return results

    def save_test_results(self, results: list[TestResult]) -> None:
        """Save test results to a timestamped file."""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        file_path = self.test_data_dir / "results" / f"test_results_{timestamp}.json"

        serializable_results = []
        for result in results:
            result_dict = asdict(result)
            result_dict["actual_output"] = self._filter_excluded_attributes(
                result_dict["actual_output"]
            )
            if result_dict["expected_output"]:
                result_dict["expected_output"] = self._filter_excluded_attributes(
                    result_dict["expected_output"]
                )
            if result_dict.get("token_usage"):
                result_dict["token_usage"] = self._summarize_token_usage(
                    result_dict["token_usage"]
                )
            # Remove execution_time from saved results
            if "execution_time" in result_dict:
                del result_dict["execution_time"]
            serializable_results.append(result_dict)
        with open(file_path, "w") as f:
            json.dump(serializable_results, f, indent=2)
        logger.info(f"Saved test results to {file_path}")

    def _compare_outputs(
        self, actual: dict[str, Any], expected: dict[str, Any]
    ) -> dict[str, Any]:
        """Compare actual output with expected output and return differences."""
        differences = {}
        filtered_actual = self._filter_excluded_attributes(actual)
        filtered_expected = self._filter_excluded_attributes(expected)

        all_keys = set(filtered_actual.keys()) | set(filtered_expected.keys())
        for key in all_keys:
            if filtered_actual.get(key) != filtered_expected.get(key):
                differences[key] = {
                    "expected": filtered_expected.get(key),
                    "actual": filtered_actual.get(key),
                }
        return differences

    def _compare_regression_metrics(
        self,
        actual: dict[str, Any],
        expected: dict[str, Any],
        actual_token_usage: Optional[dict[str, Any]],
        expected_token_usage: Optional[dict[str, Any]],
    ) -> dict[str, Any]:
        """Compare only quality scores, token usage, and quality gate failures for regression testing."""
        differences = {}

        # Check for missing or empty output
        if not actual or len(actual) == 0:
            differences["missing_output"] = {
                "expected": "Non-empty output",
                "actual": "Empty or missing output",
                "reason": "Test produced no output",
            }
            return differences

        # Compare quality scores
        quality_score_fields = [
            key for key in actual.keys() if key.endswith("_quality_score")
        ]
        for field in quality_score_fields:
            actual_score = actual.get(field)
            expected_score = expected.get(field)

            if actual_score is not None and expected_score is not None:
                # Check if score is below 8 or 20% worse
                if actual_score < 8.0:
                    differences[f"{field}_below_threshold"] = {
                        "expected": f">= 8.0",
                        "actual": actual_score,
                        "reason": "Quality score below minimum threshold of 8.0",
                    }
                elif actual_score < expected_score * 0.8:  # 20% worse
                    differences[f"{field}_regression"] = {
                        "expected": f">= {expected_score * 0.8:.1f}",
                        "actual": actual_score,
                        "reason": f"Quality score {((expected_score - actual_score) / expected_score * 100):.1f}% worse than expected",
                    }

        # Compare quality gate failures
        quality_approved_fields = [
            key for key in actual.keys() if key.endswith("_quality_approved")
        ]
        actual_failed_gates = sum(
            1 for field in quality_approved_fields if actual.get(field) is False
        )
        expected_failed_gates = sum(
            1 for field in quality_approved_fields if expected.get(field) is False
        )

        if actual_failed_gates != expected_failed_gates:
            differences["quality_gate_failures"] = {
                "expected": expected_failed_gates,
                "actual": actual_failed_gates,
                "reason": f"Number of failed quality gates changed from {expected_failed_gates} to {actual_failed_gates}",
            }

        # Check for specific quality gate failures
        failed_gates = []
        for field in quality_approved_fields:
            if actual.get(field) is False:
                gate_name = field.replace("_quality_approved", "")
                failed_gates.append(gate_name)

        if failed_gates:
            differences["specific_quality_gate_failures"] = {
                "expected": "All quality gates passed",
                "actual": f"Failed gates: {', '.join(failed_gates)}",
                "reason": f"Quality gates failed for: {', '.join(failed_gates)}",
            }

        # Compare token usage (20% more is an error)
        if actual_token_usage and expected_token_usage:
            actual_tokens = actual_token_usage.get("total_tokens", 0)
            expected_tokens = expected_token_usage.get("total_tokens", 0)

            if (
                expected_tokens > 0 and actual_tokens > expected_tokens * 1.2
            ):  # 20% more
                differences["token_usage_regression"] = {
                    "expected": f"<= {expected_tokens * 1.2:.0f}",
                    "actual": actual_tokens,
                    "reason": f"Token usage {((actual_tokens - expected_tokens) / expected_tokens * 100):.1f}% higher than expected",
                }

        return differences

    def _format_value_for_diff(self, value: Any, indent: int = 0) -> str:
        """Format a value for diff display with proper indentation."""
        indent_str = "  " * indent
        if isinstance(value, dict):
            if not value:
                return "{}"
            lines = ["{"]
            for k, v in value.items():
                lines.append(
                    f"{indent_str}  {repr(k)}: {self._format_value_for_diff(v, indent + 1)},"
                )
            lines.append(f"{indent_str}}}")
            return "\n".join(lines)
        elif isinstance(value, list):
            if not value:
                return "[]"
            lines = ["["]
            for item in value:
                lines.append(
                    f"{indent_str}  {self._format_value_for_diff(item, indent + 1)},"
                )
            lines.append(f"{indent_str}]")
            return "\n".join(lines)
        else:
            return repr(value)

    def print_colored_diff(
        self, actual: dict[str, Any], expected: dict[str, Any]
    ) -> None:
        """Print a colored diff between actual and expected outputs directly to console."""
        console.print(Panel("DETAILED DIFF", style="cyan bold", width=60, expand=False))

        all_keys = sorted(set(actual.keys()) | set(expected.keys()))

        for key in all_keys:
            actual_value = actual.get(key)
            expected_value = expected.get(key)

            if actual_value == expected_value:
                continue

            console.print(f"\n[yellow bold]~ CHANGED: {key}[/yellow bold]")

            expected_panel = Panel(
                self._format_value_for_diff(expected_value),
                border_style="red",
                title="Expected",
            )
            actual_panel = Panel(
                self._format_value_for_diff(actual_value),
                border_style="green",
                title="Actual",
            )
            console.print(Columns([expected_panel, actual_panel]))

    def print_regression_diff(
        self,
        actual: dict[str, Any],
        expected: dict[str, Any],
        actual_token_usage: Optional[dict[str, Any]],
        expected_token_usage: Optional[dict[str, Any]],
        test_result: Optional["TestResult"] = None,
    ) -> None:
        """Print a focused diff for regression testing showing only quality scores, token usage, and quality gates."""
        console.print(
            Panel("REGRESSION METRICS DIFF", style="cyan bold", width=60, expand=False)
        )

        differences = self._compare_regression_metrics(
            actual, expected, actual_token_usage, expected_token_usage
        )

        # Check for other failure reasons
        other_issues = []

        # Check if test had an execution error
        if test_result and test_result.error:
            other_issues.append(f"Execution Error: {test_result.error}")

        # Check if actual output is empty or missing key fields
        if not actual or len(actual) == 0:
            other_issues.append("No output generated")
        elif expected and len(expected) > 0:
            # Check for missing key fields that should be present
            key_fields = ["target_word", "source_word", "validation_passed"]
            missing_fields = [
                field
                for field in key_fields
                if field in expected and field not in actual
            ]
            if missing_fields:
                other_issues.append(f"Missing key fields: {', '.join(missing_fields)}")

        # Check for quality gate failures
        if actual:
            quality_gates = [
                key for key in actual.keys() if key.endswith("_quality_approved")
            ]
            failed_gates = [
                gate.replace("_quality_approved", "")
                for gate in quality_gates
                if actual.get(gate) is False
            ]
            if failed_gates:
                other_issues.append(f"Failed quality gates: {', '.join(failed_gates)}")

        if not differences and not other_issues:
            console.print("[green]✓ No regression issues detected[/green]")
            return

        # Show regression differences
        for key, diff in differences.items():
            console.print(f"\n[yellow bold]~ REGRESSION: {key}[/yellow bold]")
            console.print(f"[red]Reason: {diff['reason']}[/red]")

            expected_panel = Panel(
                str(diff["expected"]),
                border_style="red",
                title="Expected",
            )
            actual_panel = Panel(
                str(diff["actual"]),
                border_style="green",
                title="Actual",
            )
            console.print(Columns([expected_panel, actual_panel]))

        # Show other issues
        for issue in other_issues:
            console.print(f"\n[red bold]~ ISSUE: {issue}[/red bold]")

    def print_colored_test_report(self, results: list[TestResult]) -> None:
        """Print a colored test report with detailed diffs for regression testing directly to console."""
        total_tests = len(results)
        passed_tests = sum(1 for r in results if r.passed)
        failed_tests = total_tests - passed_tests

        console.print(
            Panel(
                "[cyan bold]LANGGRAPH REGRESSION TEST REPORT[/cyan bold]", expand=False
            )
        )
        console.print(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

        # Calculate token usage statistics
        total_tokens = 0
        total_input_tokens = 0
        total_output_tokens = 0
        total_execution_time = 0.0
        tests_with_tokens = 0

        for result in results:
            if result.token_usage:
                total_tokens += result.token_usage.get("total_tokens", 0)
                total_input_tokens += result.token_usage.get("total_input_tokens", 0)
                total_output_tokens += result.token_usage.get("total_output_tokens", 0)
                tests_with_tokens += 1
            if result.execution_time:
                total_execution_time += result.execution_time

        # Summary table
        summary_table = Table(title="[cyan bold]SUMMARY[/cyan bold]")
        summary_table.add_column("Metric", style="cyan")
        summary_table.add_column("Value", style="bold")
        summary_table.add_row("Total Tests", str(total_tests))
        summary_table.add_row("Passed", f"[green]{passed_tests}[/green]")
        summary_table.add_row("Failed", f"[red]{failed_tests}[/red]")
        if total_tests > 0:
            success_rate = (passed_tests / total_tests) * 100
            color = (
                "green"
                if success_rate >= 90
                else "yellow" if success_rate >= 70 else "red"
            )
            summary_table.add_row(
                "Success Rate", f"[{color}]{success_rate:.1f}%[/{color}]"
            )

        # Add token usage statistics
        if tests_with_tokens > 0:
            summary_table.add_row(
                "Total Execution Time", f"{total_execution_time:.2f}s"
            )
            summary_table.add_row("Total Tokens Used", f"{total_tokens:,}")
            summary_table.add_row("Input Tokens", f"{total_input_tokens:,}")
            summary_table.add_row("Output Tokens", f"{total_output_tokens:,}")
            summary_table.add_row(
                "Avg Tokens per Test", f"{total_tokens // tests_with_tokens:,}"
            )

        console.print(summary_table)

        # Detailed test results table
        if total_tests <= 10:  # Show detailed table for small test suites
            console.print("\n[cyan bold]DETAILED TEST RESULTS[/cyan bold]")
            results_table = Table()
            results_table.add_column("Test ID", style="cyan", width=30)
            results_table.add_column("Status", style="bold", width=8)
            results_table.add_column("Execution Time", width=15)
            results_table.add_column("Tokens", width=12)
            results_table.add_column("Regression", width=15)

            for r in results:
                # Status
                status = "[green]✓ PASS[/green]" if r.passed else "[red]✗ FAIL[/red]"

                # Execution time
                exec_time = f"{r.execution_time:.2f}s" if r.execution_time else "N/A"

                # Token usage
                tokens = "N/A"
                if r.token_usage:
                    tokens = f"{r.token_usage.get('total_tokens', 0):,}"

                # Regression analysis
                regression = "N/A"
                if r.expected_output and r.actual_output and r.token_usage:
                    # Compare with expected values
                    expected_tokens = 0
                    expected_time = 0
                    if hasattr(r, "expected_token_usage") and r.expected_token_usage:
                        expected_tokens = r.expected_token_usage.get("total_tokens", 0)
                        expected_time = r.expected_token_usage.get(
                            "total_execution_time", 0
                        )

                    current_tokens = r.token_usage.get("total_tokens", 0)
                    current_time = r.execution_time or 0

                    regressions = []
                    if expected_tokens > 0:
                        token_diff = (
                            (current_tokens - expected_tokens) / expected_tokens
                        ) * 100
                        if token_diff > 20:
                            regressions.append(f"Tokens +{token_diff:.0f}%")
                        elif token_diff < -20:
                            regressions.append(f"Tokens {token_diff:.0f}%")

                    if expected_time > 0:
                        time_diff = (
                            (current_time - expected_time) / expected_time
                        ) * 100
                        if time_diff > 20:
                            regressions.append(f"Time +{time_diff:.0f}%")
                        elif time_diff < -20:
                            regressions.append(f"Time {time_diff:.0f}%")

                    # Check quality scores
                    if r.expected_output and r.actual_output:
                        expected_scores = self._extract_quality_scores(
                            r.expected_output
                        )
                        actual_scores = self._extract_quality_scores(r.actual_output)

                        for tool, expected_score in expected_scores.items():
                            actual_score = actual_scores.get(tool, 0)
                            if actual_score < 8 or (
                                expected_score > 0
                                and actual_score < expected_score * 0.8
                            ):
                                regressions.append(f"{tool} {actual_score:.1f}")

                    if regressions:
                        regression = ", ".join(regressions)
                    else:
                        regression = "[green]✓[/green]"

                results_table.add_row(r.test_id, status, exec_time, tokens, regression)

            console.print(results_table)

        # Show passed/failed test lists
        if passed_tests > 0:
            console.print("\n[green bold]PASSED TESTS:[/green bold]")
            for r in results:
                if r.passed:
                    exec_time = (
                        f" ({r.execution_time:.2f}s)" if r.execution_time else ""
                    )
                    token_info = ""
                    if r.token_usage:
                        tokens = r.token_usage.get("total_tokens", 0)
                        token_info = f" [{tokens:,} tokens]"
                    console.print(
                        f"  [green]✓[/green] {r.test_id}{exec_time}{token_info}"
                    )

        if failed_tests > 0:
            console.print("\n[red bold]FAILED TESTS:[/red bold]")
            for r in results:
                if not r.passed:
                    exec_time = (
                        f" ({r.execution_time:.2f}s)" if r.execution_time else ""
                    )
                    token_info = ""
                    if r.token_usage:
                        tokens = r.token_usage.get("total_tokens", 0)
                        token_info = f" [{tokens:,} tokens]"
                    console.print(f"  [red]✗[/red] {r.test_id}{exec_time}{token_info}")
                    if r.error:
                        console.print(f"    [red]Error: {r.error}[/red]")
                    elif r.expected_output and r.actual_output:
                        filtered_actual = self._filter_excluded_attributes(
                            r.actual_output
                        )
                        filtered_expected = self._filter_excluded_attributes(
                            r.expected_output
                        )
                        # Use regression-specific diff for better focus
                        self.print_regression_diff(
                            filtered_actual,
                            filtered_expected,
                            r.token_usage,
                            getattr(r, "expected_token_usage", None),
                            r,
                        )
                    console.print()

    def _extract_quality_scores(self, output: dict[str, Any]) -> dict[str, float]:
        """Extract quality scores from the output dictionary."""
        scores = {}
        for key, value in output.items():
            if key.endswith("_quality_score") and isinstance(value, (int, float)):
                tool_name = key.replace("_quality_score", "")
                scores[tool_name] = float(value)
        return scores

    def _make_serializable(self, obj: Any) -> Any:
        """Recursively convert objects to JSON serializable format."""
        if isinstance(obj, (str, int, float, bool, type(None))):
            return obj
        if hasattr(obj, "model_dump"):
            return obj.model_dump()
        if hasattr(obj, "value"):  # Enums
            return obj.value
        if isinstance(obj, dict):
            return {k: self._make_serializable(v) for k, v in obj.items()}
        if isinstance(obj, (list, tuple, set)):
            return [self._make_serializable(item) for item in obj]
        if hasattr(obj, "__dict__"):
            return {
                k: self._make_serializable(v)
                for k, v in obj.__dict__.items()
                if not k.startswith("_")
            }
        try:
            return str(obj)
        except Exception:
            return f"<unserializable: {type(obj).__name__}>"
