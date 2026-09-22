from __future__ import annotations

from collections.abc import Callable

from data_analyst_agent.application.chat_use_case import execute_chat_turn
from data_analyst_agent.application.research_use_case import research_question


def get_chat_use_case() -> Callable:
    return execute_chat_turn


def get_research_use_case() -> Callable:
    return research_question
