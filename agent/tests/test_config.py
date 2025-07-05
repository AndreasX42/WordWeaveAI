from pathlib import Path
from typing import Any

# Test Framework Configuration
TEST_CONFIG = {
    "test_data_dir": "test_data",
}


# Sample Test Data Templates
SAMPLE_TEST_CASES = [
    {
        "category": "basic_translation",
        "cases": [
            {
                "source_word": "el edificio",
                "target_language": "German",
                "description": "English noun to Spanish",
                "expected_pos": "noun",
                "tags": ["english", "spanish", "noun", "basic"],
            },
            # {
            #     "source_word": "comer",
            #     "target_language": "English",
            #     "description": "Spanish verb to English",
            #     "expected_pos": "verb",
            #     "tags": ["spanish", "english", "verb", "basic"],
            # },
        ],
    },
    # {
    #     "category": "validation_tests",
    #     "cases": [
    #         {
    #             "source_word": "xyz123invalid",
    #             "target_language": "English",
    #             "description": "Invalid word should fail validation",
    #             "expected_validation": False,
    #             "tags": ["validation", "error_handling", "negative_test"],
    #         },
    #         {
    #             "source_word": "",
    #             "target_language": "English",
    #             "description": "Empty word should fail validation",
    #             "expected_validation": False,
    #             "tags": ["validation", "error_handling", "edge_case"],
    #         },
    #         {
    #             "source_word": "supercalifragilisticexpialidocious",
    #             "target_language": "Spanish",
    #             "description": "Very long word handling",
    #             "expected_validation": True,
    #             "tags": ["validation", "edge_case", "long_word"],
    #         },
    #     ],
    # },
    # {
    #     "category": "complex_words",
    #     "cases": [
    #         {
    #             "source_word": "serendipity",
    #             "target_language": "German",
    #             "description": "Complex English word to German",
    #             "expected_pos": "noun",
    #             "tags": ["english", "german", "complex", "noun"],
    #         },
    #         {
    #             "source_word": "schadenfreude",
    #             "target_language": "English",
    #             "description": "German compound word to English",
    #             "expected_pos": "noun",
    #             "tags": ["german", "english", "compound", "noun"],
    #         },
    #     ],
    # },
]


def get_test_config(key: str, default: Any = None) -> Any:
    """Get a configuration value."""
    return TEST_CONFIG.get(key, default)


def get_test_data_dir() -> Path:
    """Get the test data directory path."""
    # Make test_data_dir relative to the tests directory
    tests_dir = Path(__file__).parent
    test_data_dir_name = get_test_config("test_data_dir", "test_data")
    return tests_dir / test_data_dir_name


def validate_test_environment() -> dict[str, bool]:
    """Validate that the test environment is properly configured."""
    validation_results = {}

    # Get test data directory and ensure it exists
    test_dir = get_test_data_dir()
    test_dir.mkdir(exist_ok=True)
    validation_results["test_data_dir_exists"] = test_dir.exists()

    # Check if required subdirectories exist and create them if needed
    required_dirs = ["test_cases", "ground_truth", "results"]
    for dir_name in required_dirs:
        dir_path = test_dir / dir_name
        dir_path.mkdir(exist_ok=True)
        validation_results[f"{dir_name}_dir_exists"] = dir_path.exists()

    # Check if graph is importable
    try:
        from vocab_processor.agent import graph

        validation_results["graph_importable"] = True
    except ImportError:
        validation_results["graph_importable"] = False

    return validation_results
