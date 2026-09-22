from __future__ import annotations

import os
from dataclasses import dataclass

from dotenv import load_dotenv

load_dotenv()


@dataclass(frozen=True)
class APISettings:
    title: str
    version: str
    debug: bool
    shutdown_grace_seconds: float


def get_api_settings() -> APISettings:
    return APISettings(
        title=os.getenv("API_TITLE", "Data Analyst Agent"),
        version=os.getenv("API_VERSION", "0.1.0"),
        debug=os.getenv("API_DEBUG", "false").lower() == "true",
        shutdown_grace_seconds=float(os.getenv("SHUTDOWN_GRACE_SECONDS", "5")),
    )
