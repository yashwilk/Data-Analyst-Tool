from __future__ import annotations

from pydantic import BaseModel, Field


class ResearchRequest(BaseModel):
    question: str = Field(..., min_length=2, max_length=1000)


class ChartResponse(BaseModel):
    title: str
    caption: str
    chart_type: str
    image_base64: str


class ResearchResponse(BaseModel):
    answer: str
    key_findings: list[str]
    charts: list[ChartResponse]
    citations: list[str]
    queries_used: list[str]
    conversation_id: str
    status: str
