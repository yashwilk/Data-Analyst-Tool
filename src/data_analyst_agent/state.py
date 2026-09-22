"""LangGraph state shared by both the Chat graph and the Research graph.

One TypedDict for both modes, keeps every node's signature identical regardless of
which graph it's wired into
"""

from __future__ import annotations

from typing import Any, TypedDict


class QueryPlan(TypedDict):
    label: str
    sub_question: str
    sql: str


class DataAnalystState(TypedDict, total=False):
    run_id: str
    mode: str  # "chat" | "research"
    question: str

    conversation_id: str | None
    conversation_history: list[dict[str, Any]]

    scope: str
    sub_questions: list[str]
    queries: list[QueryPlan]
    query_results: list[dict[str, Any]]
    retry_count: int

    answer: str
    key_findings: list[str]
    citations: list[str]
    charts: list[dict[str, Any]]

    status: str
    errors: list[str]
    debug: dict[str, Any]
