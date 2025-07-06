import dotenv

dotenv.load_dotenv()

import argparse
import sys

from test_config import SAMPLE_TEST_CASES, validate_test_environment
from test_framework import LangGraphTestFramework, TestCase


def create_test_cases_from_config() -> list[TestCase]:
    """Create test cases from the configuration file."""
    test_cases = []

    for category_data in SAMPLE_TEST_CASES:
        category = category_data["category"]
        cases = category_data["cases"]

        for i, case_data in enumerate(cases):
            test_id = f"{category}_{i+1:02d}"

            test_case = TestCase(
                test_id=test_id,
                description=case_data["description"],
                input_data={
                    "source_word": case_data["source_word"],
                    "source_language": case_data.get("source_language", None),
                    "target_language": case_data["target_language"],
                },
                tags=case_data.get("tags", []),
            )
            test_cases.append(test_case)

    return test_cases


async def build_ground_truth_scenario(
    test_framework: LangGraphTestFramework, test_cases: list[TestCase]
):
    """Build ground truth scenario - run tests and save outputs as expected results."""
    print("🏗️  Building Ground Truth Scenario")
    print("=" * 50)

    # Add test cases to framework
    test_framework.test_cases = test_cases

    # Save test cases
    test_framework.save_test_cases()
    print(f"✅ Saved {len(test_cases)} test cases")

    # Build ground truth
    print("\n🔄 Running tests to build ground truth...")
    results = await test_framework.build_ground_truth()

    # Report results
    successful_cases = sum(1 for r in results.values() if r.passed and not r.error)
    print(f"\n📊 Ground Truth Results:")
    print(f"   Total test cases: {len(test_cases)}")
    print(f"   Successful executions: {successful_cases}")
    print(f"   Failed executions: {len(test_cases) - successful_cases}")

    return results


async def regression_test_scenario(test_framework: LangGraphTestFramework):
    """Regression test scenario - run tests against existing ground truth."""
    print("🔍 Regression Test Scenario")
    print("=" * 50)

    # Load existing test cases and ground truth
    try:
        test_framework.load_test_cases_from_file(
            test_framework.test_data_dir / "test_cases" / "test_cases.json"
        )
        test_framework.load_ground_truth()
        print(
            f"✅ Loaded {len(test_framework.test_cases)} test cases with ground truth"
        )
    except Exception as e:
        print(f"❌ Error loading test data: {e}")
        return

    # Run regression tests
    print("\n🔄 Running regression tests...")
    results = await test_framework.run_test_suite()

    # Generate and display colored report for regression tests
    test_framework.print_colored_test_report(results)

    # Also save the report to file
    report = test_framework.generate_colored_test_report(results)

    # Save detailed report
    report_file = test_framework.test_data_dir / "results" / "regression_report.txt"
    with open(report_file, "w") as f:
        f.write(report)
    print(f"📄 Detailed report saved to: {report_file}")

    return results


async def single_test_scenario(
    test_framework: LangGraphTestFramework, source_word: str, target_language: str
):
    """Run a single test case."""
    print(f"🎯 Single Test Scenario: '{source_word}' -> {target_language}")
    print("=" * 50)

    # Create single test case
    test_case = TestCase(
        test_id="single_test",
        description=f"Single test: {source_word} to {target_language}",
        input_data={"source_word": source_word, "target_language": target_language},
        tags=["single_test"],
    )

    # Run the test
    print("🔄 Running test...")
    result = await test_framework.run_single_test(test_case)

    # Display results
    print(f"\n📊 Test Result:")
    print(f"   Test ID: {result.test_id}")
    print(f"   Status: {'✅ PASSED' if result.passed else '❌ FAILED'}")
    print(f"   Execution Time: {result.execution_time:.2f}s")

    if result.error:
        print(f"   Error: {result.error}")

    # Display key outputs
    if result.actual_output:
        print(f"\n📝 Key Outputs:")
        key_fields = [
            "validation_passed",
            "source_language",
            "target_word",
            "source_part_of_speech",
            "target_part_of_speech",
        ]
        for field in key_fields:
            if field in result.actual_output:
                print(f"   {field}: {result.actual_output[field]}")

    return result


def check_environment():
    """Check if the test environment is properly configured."""
    print("🔧 Environment Check")
    print("=" * 50)

    validation_results = validate_test_environment()

    all_passed = True
    for check, passed in validation_results.items():
        status = "✅ PASS" if passed else "❌ FAIL"
        print(f"   {check}: {status}")
        if not passed:
            all_passed = False

    if not all_passed:
        print("\n⚠️  Some environment checks failed. Please fix the issues above.")
        return False

    print("\n✅ Environment check passed!")
    return True


async def main():
    """Main function to handle command line arguments and run scenarios."""
    parser = argparse.ArgumentParser(description="LangGraph Test Framework Runner")
    parser.add_argument(
        "scenario",
        choices=["build", "regression", "single", "check"],
        help="Test scenario to run",
    )
    parser.add_argument("--source-word", help="Source word for single test scenario")
    parser.add_argument(
        "--target-language", help="Target language for single test scenario"
    )
    parser.add_argument(
        "--test-data-dir",
        default="test_data",
        help="Directory for test data (default: test_data)",
    )

    args = parser.parse_args()

    # Environment check
    if args.scenario == "check":
        success = check_environment()
        sys.exit(0 if success else 1)

    # Initialize test framework
    test_framework = LangGraphTestFramework(test_data_dir=args.test_data_dir)

    try:
        if args.scenario == "build":
            # Build ground truth scenario
            test_cases = create_test_cases_from_config()
            await build_ground_truth_scenario(test_framework, test_cases)

        elif args.scenario == "regression":
            # Regression test scenario
            await regression_test_scenario(test_framework)

        elif args.scenario == "single":
            # Single test scenario
            if not args.source_word or not args.target_language:
                print(
                    "❌ Error: --source-word and --target-language are required for single test"
                )
                sys.exit(1)

            await single_test_scenario(
                test_framework, args.source_word, args.target_language
            )

        print("\n🎉 Test scenario completed successfully!")

    except Exception as e:
        print(f"\n❌ Error running test scenario: {e}")
        sys.exit(1)


if __name__ == "__main__":
    import asyncio

    asyncio.run(main())
