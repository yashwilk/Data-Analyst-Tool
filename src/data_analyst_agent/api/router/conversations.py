from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from data_analyst_agent.auth.dependencies import get_current_user
from data_analyst_agent.database import repository
from data_analyst_agent.database.database import get_db
from data_analyst_agent.database.model import User

router = APIRouter()


@router.get("/conversations")
async def list_conversations(
    db: AsyncSession = Depends(get_db), user: User = Depends(get_current_user)
) -> list[dict]:
    return await repository.get_all_conversations(db, user_id=user.id)


@router.get("/conversations/{conversation_id}")
async def get_conversation(
    conversation_id: str,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
) -> list[dict]:
    return await repository.get_conversation_turns(db, conversation_id, user_id=user.id)
