import os
import pathlib

# A file-based (not `:memory:`) SQLite DB for the app-level test DATABASE_URL:
# the app's engine hands out a *pool* of connections, and separate
# connections to `sqlite:///:memory:` are separate, empty databases --
# state written by one request (e.g. register) wouldn't be visible to
# the next (e.g. login) on a different pooled connection. A file shared
# by every connection sidesteps that without touching pool config.
_TEST_DB_PATH = pathlib.Path(__file__).parent / "_test_app.db"
_TEST_DB_PATH.unlink(missing_ok=True)
os.environ.setdefault("DATABASE_URL", f"sqlite+aiosqlite:///{_TEST_DB_PATH}")
os.environ.setdefault("GROQ_API_KEY", "test-key-not-used")
os.environ.setdefault("AUTH_SECRET_KEY", "test-secret-not-used")

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from data_analyst_agent.database.model import Base
from tests.fakes import FakeDataSourceProvider


@pytest_asyncio.fixture
async def db_session():
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    session_factory = async_sessionmaker(engine, expire_on_commit=False)
    async with session_factory() as session:
        yield session

    await engine.dispose()


@pytest.fixture
def patched_data_source(monkeypatch):
    """Swaps the app's dataset provider for a fake -- avoids requiring a
    live Supabase connection just to exercise API/auth endpoints.

    `from x import func` binds a *separate* name in each importing
    module, so patching `x.func` alone doesn't reach callers that already
    imported it -- every module that imports `get_data_source_provider`
    directly needs its own copy patched.
    """
    import data_analyst_agent.api.app as app_module
    import data_analyst_agent.api.router.dataset as dataset_module

    fake = FakeDataSourceProvider()

    async def _noop_ensure_schema_loaded() -> None:
        return None

    for module in (app_module, dataset_module):
        monkeypatch.setattr(module, "get_data_source_provider", lambda: fake)
    monkeypatch.setattr(app_module, "ensure_schema_loaded", _noop_ensure_schema_loaded)
    return fake


def pytest_sessionfinish(session, exitstatus):
    try:
        _TEST_DB_PATH.unlink(missing_ok=True)
    except PermissionError:
        pass  # Windows: sqlite file still held open by a pooled connection
