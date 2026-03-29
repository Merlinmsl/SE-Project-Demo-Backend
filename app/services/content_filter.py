from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Optional


@dataclass
class ValidationResult:
    is_valid: bool
    reason: Optional[str] = None


# Maximum allowed question length (characters)
MAX_QUESTION_LENGTH = 500

# Minimum question length to be meaningful
MIN_QUESTION_LENGTH = 3


def validate_chat_input(question: str) -> ValidationResult:
    """Validate a student's chat question before sending to the RAG pipeline."""

    text = question.strip()

    if len(text) < MIN_QUESTION_LENGTH:
        return ValidationResult(
            is_valid=False,
            reason="Your question is too short. Please ask a complete question.",
        )

    if len(text) > MAX_QUESTION_LENGTH:
        return ValidationResult(
            is_valid=False,
            reason=f"Your question is too long (max {MAX_QUESTION_LENGTH} characters). Please shorten it.",
        )

    # Check for gibberish / keyboard mash (too many consonants in a row)
    if re.search(r"[bcdfghjklmnpqrstvwxyz]{8,}", text.lower()):
        return ValidationResult(
            is_valid=False,
            reason="That doesn't look like a valid question. Please try again.",
        )

    return ValidationResult(is_valid=True)
