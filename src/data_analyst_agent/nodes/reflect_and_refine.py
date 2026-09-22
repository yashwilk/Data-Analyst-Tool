"""Retry loop: fix queries that errored or returned nothing.

Direct analogue of the reference project's `reflect_and_refine` node
(there: too few search results -> new queries; here: a failing/empty SQL
query -> a corrected one). Bounded to `MAX_QUERY_RETRIES` so a
persistently broken question can't loop forever.
"""

from __future__ import annotations

import logging

from data_analyst_agent.interfaces.data_source import DatasetSchema
from data_analyst_agent.interfaces.llm_inference import LLMProvider
from data_analyst_agent.nodes._prompt_helpers import format_schema
from data_analyst_agent.state import DataAnalystState

logger = logging.getLogger(__name__)

MAX_QUERY_RETRIES = 1


def needs_refinement(state: DataAnalystState) -> bool:
    results = state.get("query_results", [])
    if not results:
        return False
    failing = [r for r in results if r.get("error") or r.get("row_count", 0) == 0]
    return bool(failing) and state.get("retry_count", 0) < MAX_QUERY_RETRIES


def _build_prompt(failing: list[dict], schema: DatasetSchema) -> str:
    schema_text = format_schema(schema)
    problems = "\n".join(
        f"- label={r['label']} sql={r['sql']!r} "
        f"{'error=' + r['error'] if r.get('error') else 'returned 0 rows'}"
        for r in failing
    )
    return f"""These PostgreSQL queries failed or returned no rows:

{problems}

{schema_text}

Fix each one. Keep the same label. Only reference the columns above.
Respond with ONLY a JSON object, no prose, no code fences:
{{"queries": [{{"label": "...", "sql": "SELECT ..."}}]}}
"""


async def reflect_and_refine(
    state: DataAnalystState, llm: LLMProvider, schema: DatasetSchema
) -> dict:
    results = state.get("query_results", [])
    failing = [r for r in results if r.get("error") or r.get("row_count", 0) == 0]
    queries_by_label = {q["label"]: dict(q) for q in state.get("queries", [])}

    try:
        result = await llm.generate_json(_build_prompt(failing, schema))
        fixed = result.get("queries")
        if not isinstance(fixed, list):
            raise TypeError("LLM returned no fixed queries")
        for item in fixed:
            if not isinstance(item, dict):
                continue
            label = str(item.get("label", "")).strip()
            sql = str(item.get("sql", "")).strip()
            if label in queries_by_label and sql:
                queries_by_label[label]["sql"] = sql
    except Exception as exc:  # noqa: BLE001 - nodes never raise
        logger.warning("reflect_and_refine failed: %s", exc)

    return {
        "queries": list(queries_by_label.values()),
        "retry_count": state.get("retry_count", 0) + 1,
    }
