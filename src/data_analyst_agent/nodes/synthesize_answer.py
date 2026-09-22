"""Turn query results into the final answer.


- chat: short, conversational, 1 query result, no chart.
- research: longer structured markdown (Overview / Key Findings /
  Analysis / Recommendations) synthesizing every query result, feeding
  `build_charts` afterwards.

citation URLs: only labels that correspond to a real, executed query are
kept, so the LLM can't "cite" evidence that doesn't exist.
"""

from __future__ import annotations

import logging

from data_analyst_agent.interfaces.llm_inference import LLMProvider
from data_analyst_agent.state import DataAnalystState

logger = logging.getLogger(__name__)

MAX_ROWS_IN_PROMPT = 15


def _format_results(results: list[dict]) -> str:
    blocks = []
    for r in results:
        if r.get("error"):
            blocks.append(f"### {r['label']}\nsql: {r['sql']}\nERROR: {r['error']}")
            continue
        rows_preview = r.get("rows", [])[:MAX_ROWS_IN_PROMPT]
        blocks.append(
            f"### {r['label']}\n"
            f"sql: {r['sql']}\n"
            f"row_count: {r.get('row_count', 0)}\n"
            f"rows: {rows_preview}"
        )
    return "\n\n".join(blocks) if blocks else "(no results)"


def _clean_citations(raw: object, known_labels: set[str]) -> list[str]:
    if not isinstance(raw, list):
        return sorted(known_labels)
    cleaned = [str(c).strip() for c in raw if str(c).strip() in known_labels]
    return cleaned or sorted(known_labels)


def _chat_prompt(state: DataAnalystState, results_text: str) -> str:
    from data_analyst_agent.nodes._prompt_helpers import format_conversation_history

    history = format_conversation_history(state.get("conversation_history", []))
    return f"""You are a data analyst chatbot answering questions about a
customer purchase dataset, conversationally and concisely (2-5 sentences).
Use the actual numbers from the query result below. If the result has an
error or is empty, say so plainly instead of inventing numbers.

Conversation so far:
{history}

User question: {state.get("question", "")}

Query result:
{results_text}

Respond with ONLY a JSON object, no prose, no code fences:
{{"answer": "...", "citations": ["<label>", ...]}}
"""


def _research_prompt(state: DataAnalystState, results_text: str) -> str:
    return f"""You are a data analyst writing a short research report about a
customer purchase dataset.

User question: {state.get("question", "")}
Scope: {state.get("scope", "")}

Query results (one per sub-question/facet):
{results_text}

Write a markdown report with these exact sections: "## Overview",
"## Key Findings", "## Analysis", "## Recommendations". Reference actual
numbers from the query results. If a query errored or returned nothing,
acknowledge the gap instead of inventing data.

Respond with ONLY a JSON object, no prose, no code fences:
{{"answer": "<full markdown report>", "key_findings": ["...", ...], "citations": ["<label>", ...]}}
"""


async def synthesize_answer(state: DataAnalystState, llm: LLMProvider) -> dict:
    mode = state.get("mode", "chat")
    results = state.get("query_results", [])
    known_labels = {r["label"] for r in results}
    results_text = _format_results(results)

    prompt = _chat_prompt(state, results_text) if mode == "chat" else _research_prompt(state, results_text)

    try:
        result = await llm.generate_json(prompt)
        answer = str(result.get("answer", "")).strip()
        if not answer:
            raise ValueError("LLM returned an empty answer")
        citations = _clean_citations(result.get("citations"), known_labels)
        update: dict = {"answer": answer, "citations": citations}
        if mode == "research":
            key_findings = result.get("key_findings")
            update["key_findings"] = (
                [str(f).strip() for f in key_findings if str(f).strip()]
                if isinstance(key_findings, list)
                else []
            )
        return update
    except Exception as exc:  # noqa: BLE001 - nodes never raise
        logger.warning("synthesize_answer failed: %s", exc)
        return {
            "answer": "",
            "citations": [],
            "errors": state.get("errors", []) + [f"synthesize_answer: {exc}"],
        }
