import pytest

from data_analyst_agent.application.exceptions import ApplicationError
from data_analyst_agent.application.question_validation import (
    validate_and_clean_question,
)


def test_valid_question_is_stripped():
    assert validate_and_clean_question("  what are total sales?  ") == "what are total sales?"


@pytest.mark.parametrize("bad", [123, None, "", "  ", "a", "!!!"])
def test_invalid_questions_raise(bad):
    with pytest.raises(ApplicationError):
        validate_and_clean_question(bad)


def test_too_long_question_raises():
    with pytest.raises(ApplicationError):
        validate_and_clean_question("a" * 1001)
