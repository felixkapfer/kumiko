"""Kumiko development and container entry point."""

from kumiko.adbs_legacy import (
    BEGINNER_EXPLANATIONS,
    load_content,
    validate_question,
)
from kumiko.web import main

__all__ = [
    "BEGINNER_EXPLANATIONS",
    "load_content",
    "main",
    "validate_question",
]


if __name__ == "__main__":
    main()
