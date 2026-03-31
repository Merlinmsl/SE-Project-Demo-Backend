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

# Subject scope keywords — used to check if a question is roughly on-topic
SUBJECT_KEYWORDS: dict[str, list[str]] = {
    "science": [
        "atom", "cell", "energy", "force", "gravity", "plant", "animal",
        "chemical", "reaction", "molecule", "organism", "photosynthesis",
        "ecosystem", "electricity", "magnet", "wave", "light", "sound",
        "matter", "element", "compound", "biology", "physics", "chemistry",
        "experiment", "hypothesis", "temperature", "pressure", "mass",
    ],
    "maths": [
        "equation", "number", "algebra", "geometry", "fraction", "decimal",
        "angle", "triangle", "circle", "area", "volume", "perimeter",
        "percentage", "ratio", "graph", "function", "probability",
        "calculate", "solve", "formula", "addition", "subtraction",
        "multiply", "divide", "integer", "variable", "theorem",
    ],
    "english": [
        "grammar", "noun", "verb", "adjective", "adverb", "sentence",
        "paragraph", "essay", "vocabulary", "synonym", "antonym",
        "tense", "plural", "singular", "pronoun", "preposition",
        "comprehension", "writing", "reading", "spelling", "language",
    ],
    "ict": [
        "computer", "software", "hardware", "internet", "programming",
        "database", "algorithm", "network", "binary", "code", "website",
        "html", "data", "storage", "processor", "memory", "input", "output",
    ],
}


# Harmful / inappropriate content blocklist
BLOCKED_PATTERNS: list[str] = [
    # violence and threats
    r"\b(kill|murder|attack|bomb|weapon|gun|shoot|stab|destroy|terror)\b",
    # self-harm
    r"\b(suicide|self.?harm|cut myself|end my life)\b",
    # explicit content
    r"\b(sex|porn|nude|naked|xxx)\b",
    # drugs and illegal
    r"\b(drugs|cocaine|heroin|weed|marijuana|meth)\b",
    # harassment and hate
    r"\b(hate|racist|slur|bully|harass)\b",
    # profanity (common)
    r"\b(fuck|shit|bitch|ass|damn|crap|bastard|dick|pussy)\b",
]

BLOCKED_MESSAGE = (
    "I can only help with your studies. "
    "Please ask a question related to your school subjects."
)


def check_harmful_content(question: str) -> ValidationResult:
    """Check if a question contains harmful or inappropriate content."""
    q_lower = question.lower().strip()

    for pattern in BLOCKED_PATTERNS:
        if re.search(pattern, q_lower):
            return ValidationResult(is_valid=False, reason=BLOCKED_MESSAGE)

    return ValidationResult(is_valid=True)


def check_subject_relevance(question: str, subject: Optional[str] = None) -> bool:
    """Check if a question is at least loosely related to the given subject."""
    if not subject:
        return True  # no subject filter, allow anything

    keywords = SUBJECT_KEYWORDS.get(subject.lower(), [])
    if not keywords:
        return True  # unknown subject, don't block

    q_lower = question.lower()
    return any(kw in q_lower for kw in keywords)


# Prompt injection patterns — attempts to override AI instructions
INJECTION_PATTERNS: list[str] = [
    r"ignore (all |your |previous )?instructions",
    r"ignore (all |your |previous )?rules",
    r"forget (all |your |previous )?instructions",
    r"pretend (you are|to be|you're)",
    r"act as (if|a|an)",
    r"you are now",
    r"new instructions",
    r"override (your |the )?system",
    r"disregard (your |the |all )?rules",
    r"jailbreak",
    r"do anything now",
    r"developer mode",
    r"sudo mode",
    r"bypass (your |the |all )?filter",
]

INJECTION_MESSAGE = (
    "I noticed your message looks like it's trying to change my instructions. "
    "I'm here to help you study — please ask a question about your lessons!"
)


def check_prompt_injection(question: str) -> ValidationResult:
    """Detect attempts to override the AI's system instructions."""
    q_lower = question.lower().strip()

    for pattern in INJECTION_PATTERNS:
        if re.search(pattern, q_lower):
            return ValidationResult(is_valid=False, reason=INJECTION_MESSAGE)

    return ValidationResult(is_valid=True)


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
