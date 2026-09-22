"""Dataset table configuration.

The dataset lives as a `purchases` table in the same Supabase Postgres
instance as `users`/`analysis_runs` (loaded there once via
`scripts/upload_dataset.py`), but LLM-generated SQL should run as the
least-privilege `dataset_reader` role (see `docs/dataset_reader_role.sql`)
via `DATASET_DATABASE_URL`, so the database itself stops it from reading
`users`/`analysis_runs`. Falls back to `DATABASE_URL` if unset.
"""

from __future__ import annotations

import os
from dataclasses import dataclass

from dotenv import load_dotenv

load_dotenv()


@dataclass(frozen=True)
class DataSettings:
    table_name: str
    max_result_rows: int
    database_url: str | None


def get_data_settings() -> DataSettings:
    return DataSettings(
        table_name=os.getenv("DATASET_TABLE_NAME", "purchases"),
        max_result_rows=int(os.getenv("DATASET_MAX_RESULT_ROWS", "200")),
        database_url=os.getenv("DATASET_DATABASE_URL") or None,
    )
