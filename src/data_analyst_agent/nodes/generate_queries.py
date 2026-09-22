"""Turn each sub-question into a concrete SQL SELECT query."""

from __future__ import annotations

import logging

from data_analyst_agent.interfaces.data_source import DatasetSchema
from data_analyst_agent.interfaces.llm_inference import LLMProvider
from data_analyst_agent.nodes._prompt_helpers import format_schema
from data_analyst_agent.state import DataAnalystState

logger = logging.getLogger(__name__)


def _build_prompt(sub_questions: list[str], schema: DatasetSchema) -> str:
    schema_text = format_schema(schema)
    facets = "\n".join(f"{i + 1}. {q}" for i, q in enumerate(sub_questions))

    return f"""You write PostgreSQL SQL against a single table.

{schema_text}

For each numbered sub-question below, write ONE SQL SELECT query
(PostgreSQL dialect) that answers it. Rules:
- SELECT statements only. No semicolons, no comments, no DDL/DML.
- Only reference the table and columns shown above.
- Prefer aggregations (GROUP BY, SUM, AVG, COUNT) over dumping raw rows.
- Always ORDER BY something meaningful and LIMIT results to at most 50 rows.
- Give each query a short snake_case label.

Sub-questions:
{facets}

Respond with ONLY a JSON object, no prose, no code fences:
{{"queries": [{{"label": "...", "sub_question": "...", "sql": "SELECT ..."}}]}}
"""


def _fallback_query(table_name: str, sub_question: str, index: int) -> dict:
    return {
        "label": f"fallback_{index}",
        "sub_question": sub_question,
        "sql": f"SELECT * FROM {table_name} LIMIT 20",
    }


async def generate_queries(
    state: DataAnalystState, llm: LLMProvider, schema: DatasetSchema
) -> dict:
    sub_questions = state.get("sub_questions") or [state.get("question", "")]
    prompt = _build_prompt(sub_questions, schema)

    try:
        result = await llm.generate_json(prompt)
        raw_queries = result.get("queries")
        if not isinstance(raw_queries, list) or not raw_queries:
            raise ValueError("LLM returned no queries")

        queries = []
        for i, item in enumerate(raw_queries):
            if not isinstance(item, dict) or not item.get("sql"):
                continue
            queries.append(
                {
                    "label": str(item.get("label") or f"query_{i}").strip(),
                    "sub_question": str(item.get("sub_question") or sub_questions[min(i, len(sub_questions) - 1)]),
                    "sql": str(item["sql"]).strip(),
                }
            )
        if not queries:
            raise ValueError("No usable queries in LLM response")
        return {"queries": queries}
    except Exception as exc:  # noqa: BLE001 - nodes never raise
        logger.warning("generate_queries failed, using fallback: %s", exc)
        fallback = [
            _fallback_query(schema["table_name"], q, i)
            for i, q in enumerate(sub_questions)
        ]
        return {
            "queries": fallback,
            "errors": state.get("errors", []) + [f"generate_queries: {exc}"],
        }
