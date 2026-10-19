from payment_service.core.db.models import Tariff
from payment_service.repositories.tariffs import TariffRepository


class TariffService:
    def __init__(self, repository: TariffRepository) -> None:
        self.repository = repository

    async def list_tariffs(self) -> list[Tariff]:
        return await self.repository.list()
