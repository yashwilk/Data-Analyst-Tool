"""Unit tests for the pure/offline parts of the Postgres data source provider.

Schema loading and query execution require a live Supabase connection,
so they're verified manually/via the app's startup check rather than in
the hermetic test suite -- only the SQL-safety and DSN-translation logic
(no network) is covered here.
"""

import pytest

from data_analyst_agent.services.data_source_provider_postgres import (
    UnsafeQueryError,
    _ensure_read_only,
    to_asyncpg_dsn,
)


@pytest.mark.parametrize(
    "sql",
    [
        "DROP TABLE purchases",
        "SELECT * FROM purchases; DROP TABLE purchases",
        "INSERT INTO purchases VALUES (1,2,3)",
        "",
    ],
)
def test_ensure_read_only_rejects_unsafe_sql(sql):
    with pytest.raises(UnsafeQueryError):
        _ensure_read_only(sql)


def test_ensure_read_only_allows_select():
    assert _ensure_read_only("SELECT * FROM purchases;") == "SELECT * FROM purchases"


def test_ensure_read_only_allows_with_cte():
    sql = "WITH totals AS (SELECT 1) SELECT * FROM totals"
    assert _ensure_read_only(sql) == sql


def test_to_asyncpg_dsn_strips_driver_suffix():
    assert to_asyncpg_dsn("postgresql+asyncpg://user:pw@host:5432/db") == "postgresql://user:pw@host:5432/db"


def test_to_asyncpg_dsn_leaves_plain_dsn_unchanged():
    assert to_asyncpg_dsn("postgresql://user:pw@host:5432/db") == "postgresql://user:pw@host:5432/db"
