"""Research mode: deep, multi-facet, always includes charts.


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
from data_analyst_agent.caching.cache_service import cache_key_for_question, response_cache
from data_analyst_agent.config.logger_config import bind_run_id
from data_analyst_agent.database import repository
from data_analyst_agent.database.model import new_conversation_id
from data_analyst_agent.graph import build_graph

logger = logging.getLogger(__name__)

CACHE_TTL_SECONDS = 600


async def research_question(
    question: str, db: AsyncSession | None = None, user_id: int | None = None
) -> dict:
    cleaned_question = validate_and_clean_question(question)

    cache_key = cache_key_for_question(cleaned_question)
    cached = response_cache.get(cache_key)
    if cached is not None:
        logger.info("research cache hit")
        return cached

    conversation_id = new_conversation_id()
    initial_state = make_initial_state(
        question=cleaned_question,
        mode="research",
        conversation_id=conversation_id,
        conversation_history=[],
    )

    graph = build_graph("research")
    bind_run_id(initial_state.get("run_id", "-"))

    started = time.monotonic()
    final_state = await graph.ainvoke(initial_state)
    logger.info("research run completed in %.2fs", time.monotonic() - started)

    result = normalize_state(final_state, cleaned_question)
    result["conversation_id"] = conversation_id
    result["turn_number"] = 1
    result["charts"] = final_state.get("charts", []) or []

    if result["status"] == "completed":
        response_cache.set(cache_key, result, CACHE_TTL_SECONDS)

    if db is not None:
        try:
            charts_meta = [
                {"title": c.get("title"), "caption": c.get("caption"), "chart_type": c.get("chart_type")}
                for c in result["charts"]
            ]
            await repository.save_run(
                db,
                run_id=result["run_id"],
                conversation_id=conversation_id,
                turn_number=1,
                mode="research",
                question=cleaned_question,
                answer=result["answer"],
                queries_used=result["queries_used"],
                key_findings=result["key_findings"],
                charts_meta=charts_meta,
                citations=result["citations"],
                status=result["status"],
                errors=result["errors"],
                user_id=user_id,
            )
        except Exception:
            logger.exception("Failed to persist research run %s", result["run_id"])

    return result
