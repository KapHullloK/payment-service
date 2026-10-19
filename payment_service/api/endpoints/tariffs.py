from fastapi import APIRouter

from payment_service.api.dependencies import TariffServiceDep
from payment_service.core.db.models import Tariff
from payment_service.schemas.tariffs import TariffRead

router = APIRouter()


@router.get(
    "/tariffs",
    response_model=list[TariffRead],
    summary="Получить тарифы",
    description="Возвращает доступные тарифы и цены в копейках.",
)
async def get_tariffs(service: TariffServiceDep) -> list[Tariff]:
    return await service.list_tariffs()
