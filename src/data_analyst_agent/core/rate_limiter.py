"""Rate limiting via slowapi.

Redis-backed when `REDIS_URL` is set (limits then persist across
restarts and are shared across instances), falling back to slowapi's
built-in in-memory store otherwise -- same optional-Redis pattern as
`caching/cache_service.py`.
"""

from __future__ import annotations

import os

from dotenv import load_dotenv
from slowapi import Limiter
from slowapi.util import get_remote_address

load_dotenv()

limiter = Limiter(key_func=get_remote_address, storage_uri=os.getenv("REDIS_URL") or None)

RATE_LIMIT_CHAT = "30/minute"
RATE_LIMIT_RESEARCH = "10/minute"
