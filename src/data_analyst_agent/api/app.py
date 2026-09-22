from __future__ import annotations

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded

from data_analyst_agent.api.api_exception_handler import register_exception_handlers
from data_analyst_agent.api.router.health import router as health_router
from data_analyst_agent.api.router.v1 import create_v1_router
from data_analyst_agent.auth.router import router as auth_router
from data_analyst_agent.config.api_config import get_api_settings
from data_analyst_agent.config.logger_config import setup_logging
from data_analyst_agent.core.middleware import RequestLoggingMiddleware
from data_analyst_agent.core.rate_limiter import limiter
from data_analyst_agent.database.database import init_db
from data_analyst_agent.services.data_factory import (
    ensure_schema_loaded,
    get_data_source_provider,
)

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    setup_logging()
    await init_db()
    # Load the dataset schema once at startup (one network round trip to
    # Supabase) so a broken DATABASE_URL/table fails fast instead of
    # surfacing on someone's first chat request.
    await ensure_schema_loaded()
    schema = get_data_source_provider().get_schema()
    logger.info(
        "Dataset loaded: table=%s rows=%s columns=%s",
        schema["table_name"],
        schema["row_count"],
        len(schema["columns"]),
    )
    yield


def create_app() -> FastAPI:
    settings = get_api_settings()
    app = FastAPI(title=settings.title, version=settings.version, debug=settings.debug, lifespan=lifespan)

    app.state.limiter = limiter
    app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

    app.add_middleware(RequestLoggingMiddleware)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_methods=["*"],
        allow_headers=["*"],
    )

    register_exception_handlers(app)

    app.include_router(health_router)
    app.include_router(auth_router)
    app.include_router(create_v1_router())

    return app
