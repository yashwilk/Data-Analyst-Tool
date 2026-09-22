from __future__ import annotations

from fastapi import APIRouter

from data_analyst_agent.api.router import chat, conversations, dataset, research


def create_v1_router() -> APIRouter:
    router = APIRouter(prefix="/api/v1")
    router.include_router(chat.router, tags=["chat"])
    router.include_router(research.router, tags=["research"])
    router.include_router(dataset.router, tags=["dataset"])
    router.include_router(conversations.router, tags=["conversations"])
    return router
