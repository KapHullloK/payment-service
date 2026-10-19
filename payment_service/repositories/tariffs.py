from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncConnection, AsyncSession

from payment_service.core.db.models import Tariff


class TariffRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def list(self) -> list[Tariff]:
        result = await self.session.scalars(select(Tariff).order_by(Tariff.id))
        return list(result.all())

    async def get(self, tariff_id: int) -> Tariff | None:
        return await self.session.get(Tariff, tariff_id)

    @staticmethod
    async def seed_default_tariffs(connection: AsyncConnection) -> None:
        await connection.execute(
            insert(Tariff)
            .values(
                [
                    {"title": "basic", "price": 990000},
                    {"title": "standard", "price": 1990000},
                    {"title": "premium", "price": 2990000},
                ]
            )
            .on_conflict_do_nothing(index_elements=[Tariff.title])
        )
