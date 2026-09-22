from __future__ import annotations

import uuid

from data_analyst_agent.config.logger_config import bind_run_id
from data_analyst_agent.state import DataAnalystState


def initialize_state(state: DataAnalystState) -> dict:
    run_id = state.get("run_id") or uuid.uuid4().hex
    bind_run_id(run_id)

    errors: list[str] = []
    question = state.get("question", "")
    if not isinstance(question, str) or not question.strip():
        errors.append("Question is empty or invalid")

    return {
        "run_id": run_id,
        "status": "running",
        "errors": errors,
        "retry_count": 0,
        "queries": [],
        "query_results": [],
        "citations": [],
        "charts": [],
        "key_findings": [],
    }
