"""Structured logging + run-id correlation"""

from __future__ import annotations

import json
import logging
import os
from contextvars import ContextVar

_run_id_ctx: ContextVar[str] = ContextVar("run_id", default="-")


def bind_run_id(run_id: str) -> None:
    _run_id_ctx.set(run_id)


def get_run_id() -> str:
    return _run_id_ctx.get()


class RunContextFilter(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:
        record.run_id = get_run_id()
        return True


class JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        payload = {
            "ts": self.formatTime(record, "%Y-%m-%dT%H:%M:%S%z"),
            "level": record.levelname,
            "logger": record.name,
            "run_id": getattr(record, "run_id", "-"),
            "message": record.getMessage(),
        }
        if record.exc_info:
            payload["exc_info"] = self.formatException(record.exc_info)
        return json.dumps(payload)


def setup_logging() -> None:
    level = os.getenv("LOG_LEVEL", "INFO").upper()
    fmt = os.getenv("LOG_FORMAT", "console").lower()

    root = logging.getLogger()
    root.setLevel(level)
    root.handlers.clear()

    handler = logging.StreamHandler()
    handler.addFilter(RunContextFilter())
    if fmt == "json":
        handler.setFormatter(JsonFormatter())
    else:
        handler.setFormatter(
            logging.Formatter(
                "%(asctime)s | %(levelname)-8s | run=%(run_id)s | %(name)s | %(message)s"
            )
        )
    root.addHandler(handler)
