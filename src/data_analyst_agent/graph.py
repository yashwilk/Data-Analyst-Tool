"""Builds the LangGraph pipeline shared by Chat and Research.



    START -> init_run -> scope_question -> generate_queries -> execute_queries
                                                                     |
                                            (needs_refinement?) --> reflect_and_refine --+
                                                                     |                   |
                                                                     v                   |
                                                             synthesize_answer <---------+
                                                          (research)  |  (chat)
                                                                      v    \\
                                                               build_charts  \\
                                                                      \\      \\
                                                                       v      v
                                                                     finalize_run -> END

Any node that records an error is routed to `handle_error -> END` instead.

"""

from __future__ import annotations

from typing import Literal

from langgraph.graph import END, START, StateGraph

from data_analyst_agent.interfaces.data_source import DataSourceProvider
from data_analyst_agent.interfaces.llm_inference import LLMProvider
from data_analyst_agent.nodes.build_charts import build_charts
from data_analyst_agent.nodes.execute_queries import execute_queries
from data_analyst_agent.nodes.finalize_run import finalize_run
from data_analyst_agent.nodes.generate_queries import generate_queries
from data_analyst_agent.nodes.handle_error import handle_error
from data_analyst_agent.nodes.init_run import initialize_state
from data_analyst_agent.nodes.reflect_and_refine import (
    needs_refinement,
    reflect_and_refine,
)
from data_analyst_agent.nodes.scope_question import scope_question
from data_analyst_agent.nodes.synthesize_answer import synthesize_answer
from data_analyst_agent.services.data_factory import get_data_source_provider
from data_analyst_agent.services.llm_factory import get_llm_provider
from data_analyst_agent.state import DataAnalystState


def _route_after(next_node: str):
    def _router(state: DataAnalystState) -> str:
        return "handle_error" if state.get("errors") else next_node

    return _router


def _route_after_execute(state: DataAnalystState) -> str:
    if needs_refinement(state):
        return "reflect_and_refine"
    if state.get("errors"):
        return "handle_error"
    return "synthesize_answer"


def _route_after_synthesize(state: DataAnalystState) -> str:
    if state.get("errors"):
        return "handle_error"
    return "build_charts" if state.get("mode") == "research" else "finalize_run"


def build_graph(mode: Literal["chat", "research"]):
    llm: LLMProvider = get_llm_provider()
    data_source: DataSourceProvider = get_data_source_provider()
    schema = data_source.get_schema()

    async def _scope_question(state: DataAnalystState) -> dict:
        return await scope_question(state, llm, schema)

    async def _generate_queries(state: DataAnalystState) -> dict:
        return await generate_queries(state, llm, schema)

    async def _execute_queries(state: DataAnalystState) -> dict:
        return await execute_queries(state, data_source)

    async def _reflect_and_refine(state: DataAnalystState) -> dict:
        return await reflect_and_refine(state, llm, schema)

    async def _synthesize_answer(state: DataAnalystState) -> dict:
        return await synthesize_answer(state, llm)

    graph = StateGraph(DataAnalystState)

    graph.add_node("init_run", initialize_state)
    graph.add_node("scope_question", _scope_question)
    graph.add_node("generate_queries", _generate_queries)
    graph.add_node("execute_queries", _execute_queries)
    graph.add_node("reflect_and_refine", _reflect_and_refine)
    graph.add_node("synthesize_answer", _synthesize_answer)
    graph.add_node("build_charts", build_charts)
    graph.add_node("finalize_run", finalize_run)
    graph.add_node("handle_error", handle_error)

    graph.add_edge(START, "init_run")
    graph.add_conditional_edges(
        "init_run",
        _route_after("scope_question"),
        {"scope_question": "scope_question", "handle_error": "handle_error"},
    )
    graph.add_conditional_edges(
        "scope_question",
        _route_after("generate_queries"),
        {"generate_queries": "generate_queries", "handle_error": "handle_error"},
    )
    graph.add_conditional_edges(
        "generate_queries",
        _route_after("execute_queries"),
        {"execute_queries": "execute_queries", "handle_error": "handle_error"},
    )
    graph.add_conditional_edges(
        "execute_queries",
        _route_after_execute,
        {
            "reflect_and_refine": "reflect_and_refine",
            "synthesize_answer": "synthesize_answer",
            "handle_error": "handle_error",
        },
    )
    graph.add_edge("reflect_and_refine", "execute_queries")
    graph.add_conditional_edges(
        "synthesize_answer",
        _route_after_synthesize,
        {
            "build_charts": "build_charts",
            "finalize_run": "finalize_run",
            "handle_error": "handle_error",
        },
    )
    graph.add_edge("build_charts", "finalize_run")
    graph.add_edge("finalize_run", END)
    graph.add_edge("handle_error", END)

    return graph.compile()
