import pytest
from sqlalchemy import inspect, select, update

from payment_service.core.db.models import Tariff
from payment_service.core.db.session import get_engine
from payment_service.main import app


@pytest.mark.asyncio
async def test_migration_and_tariff_seed(database_url: str) -> None:
    async with app.router.lifespan_context(app):
        async with get_engine().begin() as connection:
            tables = await connection.run_sync(
                lambda sync_connection: inspect(sync_connection).get_table_names()
            )
            assert {"tariffs", "payments"}.issubset(tables)
            tariffs = (
                await connection.execute(select(Tariff.title, Tariff.price))
            ).all()
            assert sorted(tariffs) == [
                ("basic", 990000),
                ("premium", 2990000),
                ("standard", 1990000),
            ]
            await connection.execute(
                update(Tariff).where(Tariff.title == "basic").values(price=1)
            )

    async with app.router.lifespan_context(app):
        async with get_engine().connect() as connection:
            tariffs = (
                await connection.execute(select(Tariff.title, Tariff.price))
            ).all()
            assert len(tariffs) == 3
            assert ("basic", 1) in tariffs
