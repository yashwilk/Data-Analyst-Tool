import base64

import pytest

from data_analyst_agent.nodes.build_charts import build_charts


@pytest.mark.asyncio
async def test_build_charts_produces_bar_chart_for_categorical_data():
    state = {
        "mode": "research",
        "query_results": [
            {
                "label": "revenue_by_category",
                "sub_question": "Which category earns the most?",
                "sql": "SELECT Category, SUM(Revenue) AS total FROM purchases GROUP BY Category",
                "columns": ["Category", "total"],
                "rows": [
                    {"Category": "Electronics", "total": 1800},
                    {"Category": "Office", "total": 200},
                ],
                "row_count": 2,
                "error": None,
            }
        ],
    }

    result = await build_charts(state)

    assert len(result["charts"]) == 1
    chart = result["charts"][0]
    assert chart["chart_type"] == "bar"
    assert base64.b64decode(chart["image_base64"])[:8] == b"\x89PNG\r\n\x1a\n"


@pytest.mark.asyncio
async def test_build_charts_skips_when_not_research_mode():
    result = await build_charts({"mode": "chat", "query_results": []})
    assert result == {}


@pytest.mark.asyncio
async def test_build_charts_skips_errored_results():
    state = {
        "mode": "research",
        "query_results": [
            {"label": "bad", "rows": [], "row_count": 0, "error": "syntax error"}
        ],
    }
    result = await build_charts(state)
    assert result["charts"] == []
