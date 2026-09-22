"""Small shared helpers used by several prompt-building nodes."""

from __future__ import annotations

from data_analyst_agent.interfaces.data_source import DatasetSchema


def format_schema(schema: DatasetSchema) -> str:
    lines = [f"Table: {schema['table_name']} ({schema['row_count']} rows)", "Columns:"]
    for col in schema["columns"]:
        samples = ", ".join(repr(v) for v in col["sample_values"])
        lines.append(f"  - {col['name']} ({col['dtype']}), examples: {samples}")
    return "\n".join(lines)


def format_conversation_history(history: list[dict]) -> str:
    if not history:
        return "(no prior turns)"
    lines = []
    for turn in history:
        lines.append(f"Q: {turn.get('question', '')}")
        lines.append(f"A: {turn.get('answer', '')}")
    return "\n".join(lines)
