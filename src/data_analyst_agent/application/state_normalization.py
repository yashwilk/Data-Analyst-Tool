"""Shapes a raw graph `DataAnalystState` into the stable dict the API/DB expect.

Single place responsible for this (reused by both use cases) so malformed
graph output -- wrong types, missing keys -- never leaks past this
boundary, mirroring the reference project's `normalize_state`.
"""

from __future__ import annotations

from typing import Any


def _is_list_of_str(value: Any) -> bool:
    return isinstance(value, list) and all(isinstance(v, str) for v in value)


def _is_list_of_dict(value: Any) -> bool:
    return isinstance(value, list) and all(isinstance(v, dict) for v in value)


def make_initial_state(
    question: str,
    mode: str,
    conversation_id: str | None = None,
    conversation_history: list[dict] | None = None,
) -> dict:
    return {
        "question": question,
        "mode": mode,
        "conversation_id": conversation_id,
        "conversation_history": conversation_history or [],
    }


def normalize_state(final_state: dict, question: str) -> dict:
    answer = final_state.get("answer")
    if not isinstance(answer, str):
        answer = ""

    citations = final_state.get("citations")
    if not _is_list_of_str(citations):
        citations = []

    key_findings = final_state.get("key_findings")
    if not _is_list_of_str(key_findings):
        key_findings = []

    charts = final_state.get("charts")
    if not _is_list_of_dict(charts):
        charts = []

    queries = final_state.get("queries")
    queries_used = (
        [q.get("sql", "") for q in queries if isinstance(q, dict)]
        if isinstance(queries, list)
        else []
    )

    errors = final_state.get("errors")
    if not _is_list_of_str(errors):
        errors = []

    status = final_state.get("status") if final_state.get("status") in {"completed", "error"} else "error"

    return {
        "run_id": final_state.get("run_id", ""),
        "question": question,
        "answer": answer,
        "citations": citations,
        "key_findings": key_findings,
        "charts": charts,
        "queries_used": queries_used,
        "status": status,
        "errors": errors,
    }
