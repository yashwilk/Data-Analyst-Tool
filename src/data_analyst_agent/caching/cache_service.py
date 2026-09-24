"""Response cache for the Research mode.

Redis-backed when `REDIS_URL` is set, falling back to an in-process
in-memory TTL dict otherwise. Redis here is a *local* container in
docker-compose.

Only Research is cached (deep, multi-query, multiple LLM calls -> worth
avoiding re-computation if the same question is asked twice in a demo).
Chat is deliberately never cached: it's conversation-scoped, so an
identical question string can mean something different depending on
history.
"""

from __future__ import annotations

import hashlib
import json
import logging
import os
import time
from typing import Protocol

from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)


class ResponseCache(Protocol):
    def get(self, key: str) -> dict | None: ...
    def set(self, key: str, value: dict, ttl_seconds: int) -> None: ...


class InMemoryResponseCache:
    def __init__(self) -> None:
        self._store: dict[str, tuple[float, dict]] = {}

    def get(self, key: str) -> dict | None:
        entry = self._store.get(key)
        if entry is None:
            return None
        expires_at, value = entry
        if time.monotonic() > expires_at:
            del self._store[key]
            return None
        return value

    def set(self, key: str, value: dict, ttl_seconds: int) -> None:
        self._store[key] = (time.monotonic() + ttl_seconds, value)


class RedisResponseCache:
    """Thin wrapper -- values are JSON-serialized dicts, TTL is native Redis EXPIRE."""

    _KEY_PREFIX = "data_analyst_agent:research_cache:"

    def __init__(self, redis_url: str) -> None:
        import redis  # local import: only required when REDIS_URL is set

        self._client = redis.Redis.from_url(redis_url, decode_responses=True)
        self._client.ping()

    def get(self, key: str) -> dict | None:
        try:
            raw = self._client.get(self._KEY_PREFIX + key)
        except Exception:
            logger.warning("Redis cache read failed, treating as a miss", exc_info=True)
            return None
        return json.loads(raw) if raw else None

    def set(self, key: str, value: dict, ttl_seconds: int) -> None:
        try:
            self._client.set(self._KEY_PREFIX + key, json.dumps(value), ex=ttl_seconds)
        except Exception:
            logger.warning("Redis cache write failed, continuing without caching", exc_info=True)


def cache_key_for_question(question: str) -> str:
    normalized = " ".join(question.strip().lower().split())
    return hashlib.sha256(normalized.encode("utf-8")).hexdigest()


def _build_response_cache() -> ResponseCache:
    redis_url = os.getenv("REDIS_URL")
    if redis_url:
        try:
            return RedisResponseCache(redis_url)
        except Exception:
            logger.warning("Could not connect to REDIS_URL, falling back to in-memory cache", exc_info=True)
    return InMemoryResponseCache()


response_cache: ResponseCache = _build_response_cache()
