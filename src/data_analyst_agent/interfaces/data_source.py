from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, TypedDict


class ColumnInfo(TypedDict):
    name: str
    dtype: str
    sample_values: list[Any]


class DatasetSchema(TypedDict):
    table_name: str
    row_count: int
    columns: list[ColumnInfo]


class QueryResult(TypedDict):
    label: str
    sql: str
    columns: list[str]
    rows: list[dict[str, Any]]
    row_count: int
    truncated: bool
    error: str | None


class DataSourceProvider(ABC):
    """Contract for anything that can describe + query a tabular dataset.

    """

    @abstractmethod
    def get_schema(self) -> DatasetSchema:
        raise NotImplementedError

    @abstractmethod
    async def execute_query(self, label: str, sql: str) -> QueryResult:
        raise NotImplementedError
