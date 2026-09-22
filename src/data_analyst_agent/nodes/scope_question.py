"""Interpret the user's question against the dataset schema.

Chat mode: resolve it to a single standalone sub-question (using
conversation history to fill in pronouns/references like "and last
month?"). Research mode: decompose it into 2-4 facets so the follow-up
`generate_queries` node can cover the question from multiple angles
(overall trend, breakdown by category, top/bottom performers, etc.)
instead of a single flat query.
"""

from __future__ import annotations

import logging

from data_analyst_agent.interfaces.data_source import DatasetSchema
from data_analyst_agent.interfaces.llm_inference import LLMProvider
from data_analyst_agent.nodes._prompt_helpers import (
    format_conversation_history,
    format_schema,
)
from data_analyst_agent.state import DataAnalystState

logger = logging.getLogger(__name__)

MAX_RESEARCH_FACETS = 4


def _build_prompt(state: DataAnalystState, schema: DatasetSchema) -> str:
    mode = state.get("mode", "chat")
    history = format_conversation_history(state.get("conversation_history", []))
    schema_text = format_schema(schema)

    if mode == "chat":
        facet_instruction = (
            "Return exactly ONE standalone sub-question that captures what the "
            "user is asking, resolving any pronouns/references using the "
            "conversation history (e.g. 'and last month?' -> a full question)."
        )
    else:
        facet_instruction = (
            f"Break the question into 2 to {MAX_RESEARCH_FACETS} distinct "
            "sub-questions (facets) that together give a thorough analysis "
            "-- e.g. an overall trend, a breakdown by a relevant category, "
            "and notable outliers/top performers. Each facet must be "
            "answerable with a single SQL query against the table below."
        )

    return f"""You are a data analyst scoping a question against a dataset.

Dataset schema:
{schema_text}

Conversation history:
{history}

User question: {state.get("question", "")}

{facet_instruction}

Respond with ONLY a JSON object, no prose, no code fences:
{{"scope": "<one sentence describing what will be analyzed>", "sub_questions": ["...", ...]}}
"""


def _clean_sub_questions(raw: object, mode: str) -> list[str]:
    if not isinstance(raw, list):
        return []
    cleaned = [str(q).strip() for q in raw if isinstance(q, (str, int, float)) and str(q).strip()]
    limit = 1 if mode == "chat" else MAX_RESEARCH_FACETS
    return cleaned[:limit]


async def scope_question(
    state: DataAnalystState, llm: LLMProvider, schema: DatasetSchema
) -> dict:
    prompt = _build_prompt(state, schema)
    try:
        result = await llm.generate_json(prompt)
        scope = str(result.get("scope", "")).strip()
        sub_questions = _clean_sub_questions(result.get("sub_questions"), state.get("mode", "chat"))
        if not sub_questions:
            sub_questions = [state.get("question", "")]
        return {"scope": scope or state.get("question", ""), "sub_questions": sub_questions}
    except Exception as exc:  # noqa: BLE001 - nodes never raise
        logger.warning("scope_question failed: %s", exc)
        return {
            "scope": state.get("question", ""),
            "sub_questions": [state.get("question", "")],
            "errors": state.get("errors", []) + [f"scope_question: {exc}"],
        }
