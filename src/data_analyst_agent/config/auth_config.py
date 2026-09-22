"""JWT auth settings -- same shape as the reference project's auth/config.py.

`AUTH_SECRET_KEY` must be set in production; the generated fallback is
only for local/dev convenience and changes every process restart
(invalidating existing tokens), which is a deliberate nudge not to rely
on it.
"""

from __future__ import annotations

import os
import secrets
from dataclasses import dataclass

from dotenv import load_dotenv

load_dotenv()


@dataclass(frozen=True)
class AuthSettings:
    secret_key: str
    algorithm: str
    access_token_expire_minutes: int


def get_auth_settings() -> AuthSettings:
    return AuthSettings(
        secret_key=os.getenv("AUTH_SECRET_KEY") or secrets.token_urlsafe(32),
        algorithm=os.getenv("AUTH_ALGORITHM", "HS256"),
        access_token_expire_minutes=int(os.getenv("AUTH_ACCESS_TOKEN_EXPIRE_MINUTES", "1440")),
    )
