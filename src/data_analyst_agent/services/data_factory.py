from __future__ import annotations

from data_analyst_agent.config.data_config import get_data_settings
from data_analyst_agent.config.database_config import get_database_settings
from data_analyst_agent.interfaces.data_source import DataSourceProvider
from data_analyst_agent.services.data_source_provider_postgres import (
    PostgresDataSourceProvider,
)

_provider: PostgresDataSourceProvider | None = None


def get_data_source_provider() -> DataSourceProvider:
    """Process-wide singleton connection pool to the dataset table.

    Construction here is cheap (just builds the pool lazily); the schema
    itself is loaded once via `ensure_schema_loaded()` at app startup
    (see `api/app.py`'s lifespan) since that requires a network round
    trip and `DataSourceProvider.get_schema()` is a sync method called
    from inside the (sync-friendly) graph-building code.
    """
    global _provider
    if _provider is None:
        data_settings = get_data_settings()
        db_settings = get_database_settings()
        _provider = PostgresDataSourceProvider(
            dsn=db_settings.database_url,
            table_name=data_settings.table_name,
            max_result_rows=data_settings.max_result_rows,
        )
    return _provider


async def ensure_schema_loaded() -> None:
    provider = get_data_source_provider()
    assert isinstance(provider, PostgresDataSourceProvider)
    await provider.load_schema()


def reset_data_source_provider() -> None:
    """Test-only hook to force a fresh provider on the next call."""
    global _provider
    _provider = None
