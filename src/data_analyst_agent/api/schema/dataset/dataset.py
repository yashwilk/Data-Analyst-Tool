from __future__ import annotations

from typing import Any

from pydantic import BaseModel


class ColumnResponse(BaseModel):
    name: str
    dtype: str
    sample_values: list[Any]


class DatasetSchemaResponse(BaseModel):
    table_name: str
    row_count: int
    columns: list[ColumnResponse]
