import pytest

import data_analyst_agent.graph as graph_module
from data_analyst_agent.application.chat_use_case import execute_chat_turn
from tests.fakes import FakeDataSourceProvider, default_fake_llm


@pytest.mark.asyncio
async def test_execute_chat_turn_returns_answer_and_persists(monkeypatch, db_session):
    fake_llm = default_fake_llm()
    fake_data_source = FakeDataSourceProvider()

    monkeypatch.setattr(graph_module, "get_llm_provider", lambda: fake_llm)
    monkeypatch.setattr(graph_module, "get_data_source_provider", lambda: fake_data_source)

    result = await execute_chat_turn(db_session, None, "What category earns the most revenue?")

    assert result["status"] == "completed"
    assert "Electronics" in result["answer"]
    assert result["turn_number"] == 1
    assert result["conversation_id"]

    from data_analyst_agent.database import repository

    history = await repository.get_conversation_history(db_session, result["conversation_id"])
    assert len(history) == 1
    assert history[0]["answer"] == result["answer"]


@pytest.mark.asyncio
async def test_second_turn_increments_turn_number(monkeypatch, db_session):
    fake_llm = default_fake_llm()
    fake_data_source = FakeDataSourceProvider()
    monkeypatch.setattr(graph_module, "get_llm_provider", lambda: fake_llm)
    monkeypatch.setattr(graph_module, "get_data_source_provider", lambda: fake_data_source)

    first = await execute_chat_turn(db_session, None, "Which category earns the most?")
    second = await execute_chat_turn(db_session, first["conversation_id"], "And last month?")

    assert second["conversation_id"] == first["conversation_id"]
    assert second["turn_number"] == 2
