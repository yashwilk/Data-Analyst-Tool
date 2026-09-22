from __future__ import annotations

import logging

from data_analyst_agent.config.data_config import get_data_settings
from data_analyst_agent.config.database_config import get_database_settings
from data_analyst_agent.interfaces.data_source import DataSourceProvider
from data_analyst_agent.services.data_source_provider_postgres import (
    PostgresDataSourceProvider,
)

logger = logging.getLogger(__name__)

_provider: PostgresDataSourceProvider | None = None


def get_data_source_provider() -> DataSourceProvider:
    """Process-wide singleton connection pool to the dataset table.

    """
    global _provider
    if _provider is None:
        data_settings = get_data_settings()
        dsn = data_settings.database_url
        if dsn is None:
            logger.warning(
                "DATASET_DATABASE_URL not set -- LLM-generated SQL will run with "
                "DATABASE_URL's privileges; see docs/dataset_reader_role.sql"
            )
            dsn = get_database_settings().database_url
        _provider = PostgresDataSourceProvider(
            dsn=dsn,
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
