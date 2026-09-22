from __future__ import annotations

import logging

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from data_analyst_agent.application.exceptions import ApplicationError
from data_analyst_agent.reliability.circuit_breaker import CircuitBreakerOpenError

logger = logging.getLogger(__name__)


def _error_response(status_code: int, error: str, detail: str, path: str) -> JSONResponse:
    return JSONResponse(
        status_code=status_code,
        content={"status_code": status_code, "error": error, "detail": detail, "path": path},
    )


def register_exception_handlers(app: FastAPI) -> None:
    @app.exception_handler(ApplicationError)
    async def _application_error_handler(request: Request, exc: ApplicationError):
        return _error_response(400, "application_error", str(exc), request.url.path)

    @app.exception_handler(CircuitBreakerOpenError)
    async def _circuit_breaker_handler(request: Request, exc: CircuitBreakerOpenError):
        return _error_response(
            503,
            "service_unavailable",
            f"{exc.name} is temporarily unavailable, please retry shortly",
            request.url.path,
        )

    @app.exception_handler(Exception)
    async def _unhandled_exception_handler(request: Request, exc: Exception):
        logger.exception("Unhandled exception on %s", request.url.path)
        return _error_response(500, "internal_error", "An unexpected error occurred", request.url.path)
