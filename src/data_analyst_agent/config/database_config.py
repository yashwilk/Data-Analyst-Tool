from __future__ import annotations

import os
from dataclasses import dataclass

from dotenv import load_dotenv

load_dotenv()


@dataclass(frozen=True)
class DatabaseSettings:
    database_url: str


def get_database_settings() -> DatabaseSettings:
    return DatabaseSettings(
        database_url=os.getenv(
            "DATABASE_URL", "sqlite+aiosqlite:///./data_analyst_agent.db"
        )
    )
