from __future__ import annotations

import uuid
from datetime import UTC, datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


def _utcnow() -> datetime:
    return datetime.now(UTC)


class User(Base):
    """App user -- email login with a bcrypt password hash."""

    __tablename__ = "users"

    # `Integer`, not `BigInteger`: SQLite's rowid-aliasing autoincrement only
    # kicks in for a primary key with exactly "INTEGER" type affinity --
    # this table is `bigint identity` on Postgres, but the Python-side type
    # here only needs to round-trip a plain int, which either affinity does.
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    hashed_password: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)


class AnalysisRun(Base):
    """One row per chat turn or research request.

    List/JSON-ish fields (`queries_used`, `key_findings`, `charts_meta`,
    `errors`) are stored as JSON text -- avoids a normalized schema for data
    that's always read/written as a whole blob per run.

    Chart *images* are intentionally NOT persisted (only title/caption
    metadata) to keep row sizes small; charts are regenerated on demand
    if a research run is re-executed.
    """

    __tablename__ = "analysis_runs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    run_id: Mapped[str] = mapped_column(String(64))
    conversation_id: Mapped[str] = mapped_column(String(64), index=True)
    turn_number: Mapped[int] = mapped_column(Integer, default=1)
    mode: Mapped[str] = mapped_column(String(16))
    question: Mapped[str] = mapped_column(Text)
    answer: Mapped[str] = mapped_column(Text)
    queries_used: Mapped[str] = mapped_column(Text, default="[]")
    key_findings: Mapped[str] = mapped_column(Text, default="[]")
    charts_meta: Mapped[str] = mapped_column(Text, default="[]")
    citations: Mapped[str] = mapped_column(Text, default="[]")
    status: Mapped[str] = mapped_column(String(16))
    errors: Mapped[str] = mapped_column(Text, default="[]")
    user_id: Mapped[int | None] = mapped_column(Integer, ForeignKey("users.id"), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)


def new_conversation_id() -> str:
    return uuid.uuid4().hex
