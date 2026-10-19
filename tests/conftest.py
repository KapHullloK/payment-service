from collections.abc import Iterator

import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy.engine import make_url
from testcontainers.community.postgres import PostgresContainer

from payment_service.core.config import get_settings
from payment_service.core.db.session import get_engine


@pytest.fixture
def database_url(monkeypatch: pytest.MonkeyPatch) -> Iterator[str]:
    with PostgresContainer("postgres:16") as postgres:
        url = postgres.get_connection_url(driver="asyncpg")
        database = make_url(url)
        monkeypatch.setenv("DATABASE_HOST", database.host or "localhost")
        monkeypatch.setenv("DATABASE_PORT", str(database.port or 5432))
        monkeypatch.setenv("DATABASE_USERNAME", database.username or "")
        monkeypatch.setenv("DATABASE_PASSWORD", database.password or "")
        monkeypatch.setenv("DATABASE_NAME", database.database or "")
        monkeypatch.setenv("WEBHOOK_SECRET", "test-secret")
        get_settings.cache_clear()
        get_engine.cache_clear()
        command.upgrade(Config("alembic.ini"), "head")
        yield url
        get_engine.cache_clear()
        get_settings.cache_clear()
