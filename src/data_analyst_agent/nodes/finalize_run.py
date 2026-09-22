from __future__ import annotations

from data_analyst_agent.state import DataAnalystState


def finalize_run(state: DataAnalystState) -> dict:
    has_answer = bool(state.get("answer", "").strip())
    has_errors = bool(state.get("errors"))
    status = "completed" if has_answer and not has_errors else "error"
    return {"status": status}
