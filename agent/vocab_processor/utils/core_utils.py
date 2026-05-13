import os
import re
import unicodedata

_NON_ALNUM = re.compile(r"[^a-z0-9]")


def is_lambda_context() -> bool:
    """
    Check if we're running in AWS Lambda context.

    Returns:
        True if running in Lambda, False if running locally (e.g., langgraph dev)
    """
    return os.getenv("AWS_LAMBDA_FUNCTION_NAME") is not None


def normalize_word(word: str) -> str:
    word = unicodedata.normalize("NFKC", word.lower())
    word = (
        word.replace("ß", "ss")
        .replace("ä", "ae")
        .replace("ö", "oe")
        .replace("ü", "ue")
    )
    word = "".join(
        ch
        for ch in unicodedata.normalize("NFD", word)
        if unicodedata.category(ch) != "Mn"
    )
    return _NON_ALNUM.sub("", word)
