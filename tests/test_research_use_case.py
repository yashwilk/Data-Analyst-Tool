import pytest

import data_analyst_agent.application.research_use_case as research_use_case_module
import data_analyst_agent.graph as graph_module
from data_analyst_agent.application.research_use_case import research_question
from data_analyst_agent.caching.cache_service import InMemoryResponseCache
from tests.fakes import FakeDataSourceProvider, default_fake_llm


@pytest.fixture(autouse=True)
def isolated_cache(monkeypatch):
    monkeypatch.setattr(research_use_case_module, "response_cache", InMemoryResponseCache())


@pytest.mark.asyncio
async def test_research_question_returns_report_with_charts_and_findings(monkeypatch, db_session):
    fake_llm = default_fake_llm()
    fake_data_source = FakeDataSourceProvider()
    monkeypatch.setattr(graph_module, "get_llm_provider", lambda: fake_llm)
    monkeypatch.setattr(graph_module, "get_data_source_provider", lambda: fake_data_source)

    result = await research_question("Which category performs best and why?", db_session)

    assert result["status"] == "completed"
    assert "## Key Findings" in result["answer"]
    assert result["key_findings"]
    assert len(result["charts"]) == 1
    assert result["charts"][0]["image_base64"]


@pytest.mark.asyncio
async def test_repeat_question_is_served_from_cache(monkeypatch, db_session):
    fake_llm = default_fake_llm()
    fake_data_source = FakeDataSourceProvider()
    monkeypatch.setattr(graph_module, "get_llm_provider", lambda: fake_llm)
    monkeypatch.setattr(graph_module, "get_data_source_provider", lambda: fake_data_source)

    await research_question("What drives revenue?", db_session)
    calls_after_first = len(fake_llm.calls)

    await research_question("What drives revenue?", db_session)

    assert len(fake_llm.calls) == calls_after_first
