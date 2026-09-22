from __future__ import annotations

from collections.abc import Callable

from fastapi import APIRouter, Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession

from data_analyst_agent.api.dependencies import get_research_use_case
from data_analyst_agent.api.schema.research.research import (
    ResearchRequest,
    ResearchResponse,
)
from data_analyst_agent.auth.dependencies import get_current_user
from data_analyst_agent.core.rate_limiter import RATE_LIMIT_RESEARCH, limiter
from data_analyst_agent.database.database import get_db
from data_analyst_agent.database.model import User

router = APIRouter()


@router.post("/research", response_model=ResearchResponse)
@limiter.limit(RATE_LIMIT_RESEARCH)
async def research(
    request: Request,
    body: ResearchRequest,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
    research_use_case: Callable = Depends(get_research_use_case),
) -> ResearchResponse:
    result = await research_use_case(body.question, db, user_id=user.id)
    return ResearchResponse(
        answer=result["answer"],
        key_findings=result["key_findings"],
        charts=result["charts"],
        citations=result["citations"],
        queries_used=result["queries_used"],
        conversation_id=result["conversation_id"],
        status=result["status"],
    )
