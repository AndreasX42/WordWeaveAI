import os
import re
import unicodedata


def is_lambda_context() -> bool:
    """
    Check if we're running in AWS Lambda context.

    Returns:
        True if running in Lambda, False if running locally (e.g., langgraph dev)
    """
    return os.getenv("AWS_LAMBDA_FUNCTION_NAME") is not None


def normalize_word(word: str) -> str:
    """Return lowercase, accent stripped, alnumonly version of the word."""
    _NORMALISE_RGX = re.compile(r"[^a-z0-9']")
    word = unicodedata.normalize("NFKC", word.lower())
    word = "".join(
        ch
        for ch in unicodedata.normalize("NFD", word)
        if unicodedata.category(ch) != "Mn"
    )
    return _NORMALISE_RGX.sub("", word)
