"""Run each planned SQL query against the dataset.

Per-query failures (bad column name, syntax error) are recorded on the
result itself, not pushed to `state["errors"]` -- a single failing facet
shouldn't abort the whole run. `route_after_execute` in graph.py decides
whether the failure rate is bad enough to loop back through
`reflect_and_refine`.
"""

from __future__ import annotations

from data_analyst_agent.interfaces.data_source import DataSourceProvider
from data_analyst_agent.state import DataAnalystState


async def execute_queries(
    state: DataAnalystState, data_source: DataSourceProvider
) -> dict:
    results = []
    for plan in state.get("queries", []):
        result = await data_source.execute_query(plan["label"], plan["sql"])
        results.append(dict(result))
    return {"query_results": results}
