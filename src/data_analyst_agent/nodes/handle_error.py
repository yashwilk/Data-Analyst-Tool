from __future__ import annotations

import logging

from data_analyst_agent.state import DataAnalystState

logger = logging.getLogger(__name__)


def handle_error(state: DataAnalystState) -> dict:
    """Terminal error sink. Never raises -- the graph always ends cleanly."""
    for error in state.get("errors", []):
        logger.error("run_id=%s error=%s", state.get("run_id"), error)

    answer = state.get("answer") or (
        "I couldn't complete that analysis. Please rephrase your question "
        "or ask about something else in the dataset."
    )
    return {"status": "error", "answer": answer}
