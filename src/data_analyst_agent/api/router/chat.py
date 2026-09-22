from __future__ import annotations

from collections.abc import Callable

from fastapi import APIRouter, Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession

from data_analyst_agent.api.dependencies import get_chat_use_case
from data_analyst_agent.api.schema.chat.chat import ChatRequest, ChatResponse
from data_analyst_agent.auth.dependencies import get_current_user
from data_analyst_agent.core.rate_limiter import RATE_LIMIT_CHAT, limiter
from data_analyst_agent.database.database import get_db
from data_analyst_agent.database.model import User

router = APIRouter()


@router.post("/chat", response_model=ChatResponse)
@limiter.limit(RATE_LIMIT_CHAT)
async def chat(
    request: Request,
    body: ChatRequest,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
    chat_use_case: Callable = Depends(get_chat_use_case),
) -> ChatResponse:
    result = await chat_use_case(db, body.conversation_id, body.question, user_id=user.id)
    return ChatResponse(
        answer=result["answer"],
        conversation_id=result["conversation_id"],
        turn_number=result["turn_number"],
        citations=result["citations"],
        queries_used=result["queries_used"],
        status=result["status"],
    )
