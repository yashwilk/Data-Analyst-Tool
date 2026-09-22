"""Dataset table configuration.

The dataset lives as a `purchases` table in the same Supabase Postgres
instance as `users`/`analysis_runs` (loaded there once via
`scripts/upload_dataset.py`), so it's queried through the same
`DATABASE_URL` rather than a second connection string -- see
`config/database_config.py`.
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


def get_data_settings() -> DataSettings:
    return DataSettings(
        table_name=os.getenv("DATASET_TABLE_NAME", "purchases"),
        max_result_rows=int(os.getenv("DATASET_MAX_RESULT_ROWS", "200")),
    )
