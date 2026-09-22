from __future__ import annotations

import os
from dataclasses import dataclass

from dotenv import load_dotenv

load_dotenv()


@dataclass(frozen=True)
class UISettings:
    api_base_url: str
    request_timeout: float


def get_ui_settings() -> UISettings:
    return UISettings(
        api_base_url=os.getenv("UI_API_BASE_URL", "http://localhost:8000"),
        request_timeout=float(os.getenv("UI_REQUEST_TIMEOUT", "60")),
    )
