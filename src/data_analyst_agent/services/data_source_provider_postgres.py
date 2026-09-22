"""Postgres (Supabase)-backed DataSourceProvider.

Replaces the earlier in-memory DuckDB engine: the dataset now lives as a
real `purchases` table in the same Supabase Postgres instance as
`users`/`analysis_runs`, queried over the network via a dedicated asyncpg
connection pool (kept separate from the SQLAlchemy engine used for
app-state tables -- LLM-generated, ad-hoc SQL against the dataset
shouldn't share a session/transaction scope with the ORM-mapped models).

Safety is unchanged in spirit from the DuckDB version: the LLM only ever
*proposes* SQL text; every query is passed through `_ensure_read_only`
before execution. Only a single `SELECT`/`WITH` statement is allowed --
no DDL/DML, no stacked statements. Rows returned are capped.
"""

from __future__ import annotations

import re
from datetime import date, datetime
from decimal import Decimal

import asyncpg

from data_analyst_agent.interfaces.data_source import (
    ColumnInfo,
    DatasetSchema,
    DataSourceProvider,
    QueryResult,
)

_FORBIDDEN_KEYWORDS = (
    "insert", "update", "delete", "drop", "alter", "create", "grant",
    "revoke", "truncate", "vacuum", "copy", "call", "do",
)


class UnsafeQueryError(ValueError):
    pass


def _ensure_read_only(sql: str) -> str:
    stripped = sql.strip().rstrip(";").strip()
    if not stripped:
        raise UnsafeQueryError("Empty query")
    if ";" in stripped:
        raise UnsafeQueryError("Multiple statements are not allowed")
    if not re.match(r"^\s*(select|with)\b", stripped, re.IGNORECASE):
        raise UnsafeQueryError("Only SELECT queries are allowed")
    lowered = stripped.lower()
    for keyword in _FORBIDDEN_KEYWORDS:
        if re.search(rf"\b{keyword}\b", lowered):
            raise UnsafeQueryError(f"Keyword '{keyword}' is not allowed")
    return stripped


def _jsonable(value: object) -> object:
    if isinstance(value, (datetime, date)):
        return value.isoformat()
    if isinstance(value, Decimal):
        return float(value)
    return value


def to_asyncpg_dsn(sqlalchemy_url: str) -> str:
    """`postgresql+asyncpg://...` -> `postgresql://...` (asyncpg wants a plain DSN)."""
    return sqlalchemy_url.replace("postgresql+asyncpg://", "postgresql://", 1)


class PostgresDataSourceProvider(DataSourceProvider):
    def __init__(self, dsn: str, table_name: str, max_result_rows: int) -> None:
        self._dsn = to_asyncpg_dsn(dsn)
        self._table_name = table_name
        self._max_result_rows = max_result_rows
        self._pool: asyncpg.Pool | None = None
        self._schema: DatasetSchema | None = None

    async def _get_pool(self) -> asyncpg.Pool:
        if self._pool is None:
            self._pool = await asyncpg.create_pool(self._dsn, min_size=1, max_size=5)
        return self._pool

    async def load_schema(self) -> DatasetSchema:
        """Must be awaited once at startup before get_schema()/execute_query() are used."""
        pool = await self._get_pool()
        async with pool.acquire() as conn:
            column_rows = await conn.fetch(
                "select column_name, data_type from information_schema.columns "
                "where table_schema = 'public' and table_name = $1 "
                "order by ordinal_position",
                self._table_name,
            )
            row_count = await conn.fetchval(f"select count(*) from {self._table_name}")

            columns: list[ColumnInfo] = []
            for row in column_rows:
                sample_rows = await conn.fetch(
                    f'select distinct "{row["column_name"]}" from {self._table_name} '
                    f'where "{row["column_name"]}" is not null limit 3'
                )
                samples = [_jsonable(r[row["column_name"]]) for r in sample_rows]
                columns.append(
                    ColumnInfo(name=row["column_name"], dtype=row["data_type"], sample_values=samples)
                )

        self._schema = DatasetSchema(
            table_name=self._table_name, row_count=row_count, columns=columns
        )
        return self._schema

    def get_schema(self) -> DatasetSchema:
        if self._schema is None:
            raise RuntimeError("Schema not loaded -- call load_schema() first")
        return self._schema

    async def execute_query(self, label: str, sql: str) -> QueryResult:
        try:
            safe_sql = _ensure_read_only(sql)
            limited_sql = f"select * from ({safe_sql}) as q limit {self._max_result_rows + 1}"
            pool = await self._get_pool()
            async with pool.acquire() as conn:
                records = await conn.fetch(limited_sql)
        except Exception as exc:  # noqa: BLE001 - surfaced to the node, never raised
            return QueryResult(
                label=label, sql=sql, columns=[], rows=[], row_count=0, truncated=False, error=str(exc)
            )

        truncated = len(records) > self._max_result_rows
        records = records[: self._max_result_rows]
        columns = list(records[0].keys()) if records else []
        rows = [{k: _jsonable(v) for k, v in dict(r).items()} for r in records]

        return QueryResult(
            label=label, sql=sql, columns=columns, rows=rows, row_count=len(rows),
            truncated=truncated, error=None,
        )
