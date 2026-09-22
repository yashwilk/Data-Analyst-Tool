"""Shared question validation, used identically by Pydantic schemas and use cases."""

from __future__ import annotations

from data_analyst_agent.application.exceptions import ApplicationError

MIN_LENGTH = 2
MAX_LENGTH = 1000


def validate_and_clean_question(question: object) -> str:
    if not isinstance(question, str):
        raise ApplicationError("Question must be text")

    cleaned = question.strip()
    if len(cleaned) < MIN_LENGTH:
        raise ApplicationError(f"Question must be at least {MIN_LENGTH} characters")
    if len(cleaned) > MAX_LENGTH:
        raise ApplicationError(f"Question must be at most {MAX_LENGTH} characters")
    if not any(ch.isalnum() for ch in cleaned):
        raise ApplicationError("Question must contain some alphanumeric text")

    return cleaned
