"""Chat mode: quick, conversational, multi-turn.

"""

from __future__ import annotations

import logging
import time

from sqlalchemy.ext.asyncio import AsyncSession

from data_analyst_agent.application.question_validation import (
    validate_and_clean_question,
)
from data_analyst_agent.application.state_normalization import (
    make_initial_state,
    normalize_state,
)
from data_analyst_agent.config.logger_config import bind_run_id
from data_analyst_agent.database import repository
from data_analyst_agent.database.model import new_conversation_id
from data_analyst_agent.graph import build_graph

logger = logging.getLogger(__name__)

MAX_HISTORY_TURNS = 5


async def execute_chat_turn(
    db: AsyncSession,
    conversation_id: str | None,
    question: str,
    user_id: int | None = None,
) -> dict:
    cleaned_question = validate_and_clean_question(question)

    if conversation_id:
        history = await repository.get_conversation_history(
            db, conversation_id, limit=MAX_HISTORY_TURNS
        )
        turn_number = len(history) + 1
    else:
        conversation_id = new_conversation_id()
        history = []
        turn_number = 1

    initial_state = make_initial_state(
        question=cleaned_question,
        mode="chat",
        conversation_id=conversation_id,
        conversation_history=history,
    )

    graph = build_graph("chat")
    bind_run_id(initial_state.get("run_id", "-"))

    started = time.monotonic()
    final_state = await graph.ainvoke(initial_state)
    logger.info("chat turn completed in %.2fs", time.monotonic() - started)

    result = normalize_state(final_state, cleaned_question)
    result["conversation_id"] = conversation_id
    result["turn_number"] = turn_number

    try:
        await repository.save_run(
            db,
            run_id=result["run_id"],
            conversation_id=conversation_id,
            turn_number=turn_number,
            mode="chat",
            question=cleaned_question,
            answer=result["answer"],
            queries_used=result["queries_used"],
            key_findings=result["key_findings"],
            charts_meta=[],
            citations=result["citations"],
            status=result["status"],
            errors=result["errors"],
            user_id=user_id,
        )
    except Exception:
        logger.exception("Failed to persist chat turn %s", result["run_id"])

    return result
