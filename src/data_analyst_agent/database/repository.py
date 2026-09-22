"""The ONLY module allowed to issue SQLAlchemy queries (repository pattern).

Everything else (use cases, API routers) calls these functions instead of
touching `AnalysisRun`/`User`/the session directly, so persistence
details can change (SQLite -> Postgres, this schema -> another) without
ever touching application code.
"""

from __future__ import annotations

import json

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from data_analyst_agent.database.model import AnalysisRun, User


def _serialize(value: list) -> str:
    return json.dumps(value)


def _deserialize(value: str | None) -> list:
    if not value:
        return []
    try:
        parsed = json.loads(value)
        return parsed if isinstance(parsed, list) else []
    except json.JSONDecodeError:
        return []


async def create_user(db: AsyncSession, *, email: str, hashed_password: str) -> User:
    user = User(email=email, hashed_password=hashed_password)
    db.add(user)
    await db.commit()
    await db.refresh(user)
    return user


async def get_user_by_email(db: AsyncSession, email: str) -> User | None:
    stmt = select(User).where(User.email == email)
    return (await db.execute(stmt)).scalar_one_or_none()


async def save_run(
    db: AsyncSession,
    *,
    run_id: str,
    conversation_id: str,
    turn_number: int,
    mode: str,
    question: str,
    answer: str,
    queries_used: list[str],
    key_findings: list[str],
    charts_meta: list[dict],
    citations: list[str],
    status: str,
    errors: list[str],
    user_id: int | None = None,
) -> None:
    run = AnalysisRun(
        run_id=run_id,
        conversation_id=conversation_id,
        turn_number=turn_number,
        mode=mode,
        question=question,
        answer=answer,
        queries_used=_serialize(queries_used),
        key_findings=_serialize(key_findings),
        charts_meta=_serialize(charts_meta),
        citations=_serialize(citations),
        status=status,
        errors=_serialize(errors),
        user_id=user_id,
    )
    db.add(run)
    await db.commit()


def _row_to_dict(row: AnalysisRun) -> dict:
    return {
        "run_id": row.run_id,
        "conversation_id": row.conversation_id,
        "turn_number": row.turn_number,
        "mode": row.mode,
        "question": row.question,
        "answer": row.answer,
        "queries_used": _deserialize(row.queries_used),
        "key_findings": _deserialize(row.key_findings),
        "charts_meta": _deserialize(row.charts_meta),
        "citations": _deserialize(row.citations),
        "status": row.status,
        "errors": _deserialize(row.errors),
        "created_at": row.created_at.isoformat() if row.created_at else None,
    }


async def get_conversation_history(
    db: AsyncSession, conversation_id: str, limit: int = 5
) -> list[dict]:
    stmt = (
        select(AnalysisRun)
        .where(AnalysisRun.conversation_id == conversation_id)
        .order_by(AnalysisRun.turn_number.desc())
        .limit(limit)
    )
    rows = (await db.execute(stmt)).scalars().all()
    return [_row_to_dict(r) for r in reversed(rows)]


async def get_all_conversations(db: AsyncSession, user_id: int | None = None) -> list[dict]:
    stmt = select(AnalysisRun).where(AnalysisRun.turn_number == 1)
    if user_id is not None:
        stmt = stmt.where(AnalysisRun.user_id == user_id)
    stmt = stmt.order_by(AnalysisRun.created_at.desc())
    rows = (await db.execute(stmt)).scalars().all()
    return [_row_to_dict(r) for r in rows]


async def get_conversation_turns(
    db: AsyncSession, conversation_id: str, user_id: int | None = None
) -> list[dict]:
    stmt = select(AnalysisRun).where(AnalysisRun.conversation_id == conversation_id)
    if user_id is not None:
        stmt = stmt.where(AnalysisRun.user_id == user_id)
    stmt = stmt.order_by(AnalysisRun.turn_number.asc())
    rows = (await db.execute(stmt)).scalars().all()
    return [_row_to_dict(r) for r in rows]
