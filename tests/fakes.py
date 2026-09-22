"""Fake providers so graph/use-case tests never touch Groq or the real dataset."""

from __future__ import annotations

from data_analyst_agent.interfaces.data_source import DataSourceProvider
from data_analyst_agent.interfaces.llm_inference import LLMProvider

FAKE_SCHEMA = {
    "table_name": "purchases",
    "row_count": 3,
    "columns": [
        {"name": "Category", "dtype": "object", "sample_values": ["Electronics"]},
        {"name": "Revenue", "dtype": "float64", "sample_values": [100.0]},
    ],
}


class FakeLLMProvider(LLMProvider):
    """Returns canned JSON keyed by a substring of the prompt."""

    def __init__(self, responses: dict[str, dict]) -> None:
        self._responses = responses
        self.calls: list[str] = []

    async def generate_json(self, prompt: str) -> dict:
        self.calls.append(prompt)
        for marker, response in self._responses.items():
            if marker in prompt:
                return response
        raise AssertionError(f"No fake response configured for prompt: {prompt[:200]}")


def default_fake_llm() -> FakeLLMProvider:
    return FakeLLMProvider(
        {
            "sub_questions": {
                "scope": "Revenue by category",
                "sub_questions": ["What is total revenue by category?"],
            },
            "write PostgreSQL SQL": {
                "queries": [
                    {
                        "label": "revenue_by_category",
                        "sub_question": "What is total revenue by category?",
                        "sql": "SELECT Category, SUM(Revenue) AS total FROM purchases GROUP BY Category",
                    }
                ]
            },
            "chatbot answering questions": {
                "answer": "Electronics leads with $1,800 in revenue.",
                "citations": ["revenue_by_category"],
            },
            "writing a short research report": {
                "answer": "## Overview\nElectronics leads.\n## Key Findings\n- Electronics: $1800\n## Analysis\nDetail.\n## Recommendations\nFocus on Electronics.",
                "key_findings": ["Electronics is the top category with $1800 revenue"],
                "citations": ["revenue_by_category"],
            },
        }
    )


class FakeDataSourceProvider(DataSourceProvider):
    def __init__(self, rows: list[dict] | None = None) -> None:
        self._rows = rows if rows is not None else [
            {"Category": "Electronics", "total": 1800},
            {"Category": "Office", "total": 200},
        ]

    def get_schema(self) -> dict:
        return FAKE_SCHEMA

    async def execute_query(self, label: str, sql: str) -> dict:
        return {
            "label": label,
            "sql": sql,
            "columns": list(self._rows[0].keys()) if self._rows else [],
            "rows": self._rows,
            "row_count": len(self._rows),
            "truncated": False,
            "error": None,
        }
