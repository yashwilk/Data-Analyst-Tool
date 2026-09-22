import pytest

from data_analyst_agent.reliability.circuit_breaker import (
    CircuitBreaker,
    CircuitBreakerOpenError,
    CircuitState,
)


@pytest.mark.asyncio
async def test_opens_after_threshold_failures():
    breaker = CircuitBreaker(name="test", failure_threshold=2, recovery_timeout_seconds=60)

    async def failing():
        raise RuntimeError("boom")

    for _ in range(2):
        with pytest.raises(RuntimeError):
            await breaker.call(failing)

    assert breaker.state == CircuitState.OPEN
    with pytest.raises(CircuitBreakerOpenError):
        await breaker.call(failing)


@pytest.mark.asyncio
async def test_success_resets_failure_count():
    breaker = CircuitBreaker(name="test2", failure_threshold=2)

    async def failing():
        raise RuntimeError("boom")

    async def succeeding():
        return "ok"

    with pytest.raises(RuntimeError):
        await breaker.call(failing)

    assert await breaker.call(succeeding) == "ok"
    assert breaker.state == CircuitState.CLOSED
    assert breaker.failure_count == 0
