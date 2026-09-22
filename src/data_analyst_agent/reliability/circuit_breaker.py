"""In-process circuit breaker guarding calls to the LLM provider."""

from __future__ import annotations

import time
from collections.abc import Awaitable, Callable
from dataclasses import dataclass, field
from enum import Enum
from typing import TypeVar

T = TypeVar("T")


class CircuitState(str, Enum):
    CLOSED = "closed"
    OPEN = "open"
    HALF_OPEN = "half_open"


class CircuitBreakerOpenError(Exception):
    def __init__(self, name: str) -> None:
        super().__init__(f"Circuit breaker '{name}' is open")
        self.name = name


@dataclass
class CircuitBreaker:
    name: str
    failure_threshold: int = 5
    recovery_timeout_seconds: float = 30.0
    state: CircuitState = field(default=CircuitState.CLOSED)
    failure_count: int = field(default=0)
    opened_at: float | None = field(default=None)

    def _maybe_recover(self) -> None:
        if (
            self.state == CircuitState.OPEN
            and self.opened_at is not None
            and time.monotonic() - self.opened_at >= self.recovery_timeout_seconds
        ):
            self.state = CircuitState.HALF_OPEN

    def _on_success(self) -> None:
        self.failure_count = 0
        self.state = CircuitState.CLOSED
        self.opened_at = None

    def _on_failure(self) -> None:
        self.failure_count += 1
        if self.failure_count >= self.failure_threshold:
            self.state = CircuitState.OPEN
            self.opened_at = time.monotonic()

    async def call(self, fn: Callable[[], Awaitable[T]]) -> T:
        self._maybe_recover()
        if self.state == CircuitState.OPEN:
            raise CircuitBreakerOpenError(self.name)

        try:
            result = await fn()
        except Exception:
            self._on_failure()
            raise
        else:
            self._on_success()
            return result


_breakers: dict[str, CircuitBreaker] = {}


def get_circuit_breaker(name: str) -> CircuitBreaker:
    if name not in _breakers:
        _breakers[name] = CircuitBreaker(name=name)
    return _breakers[name]
