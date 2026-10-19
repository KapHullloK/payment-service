from typing import Annotated

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from payment_service.core.db.session import get_session
from payment_service.repositories.payments import PaymentRepository
from payment_service.repositories.tariffs import TariffRepository
from payment_service.services.payments import PaymentService
from payment_service.services.pricing import PricingService
from payment_service.services.tariffs import TariffService
from payment_service.services.webhooks import WebhookService

SessionDep = Annotated[AsyncSession, Depends(get_session)]


def get_payment_repository(session: SessionDep) -> PaymentRepository:
    return PaymentRepository(session)


def get_tariff_repository(session: SessionDep) -> TariffRepository:
    return TariffRepository(session)


PaymentRepositoryDep = Annotated[PaymentRepository, Depends(get_payment_repository)]
TariffRepositoryDep = Annotated[TariffRepository, Depends(get_tariff_repository)]


def get_pricing_service() -> PricingService:
    return PricingService()


PricingServiceDep = Annotated[PricingService, Depends(get_pricing_service)]


def get_payment_service(
    payment_repository: PaymentRepositoryDep,
    tariff_repository: TariffRepositoryDep,
    pricing_service: PricingServiceDep,
) -> PaymentService:
    return PaymentService(payment_repository, tariff_repository, pricing_service)


def get_tariff_service(repository: TariffRepositoryDep) -> TariffService:
    return TariffService(repository)


def get_webhook_service(repository: PaymentRepositoryDep) -> WebhookService:
    return WebhookService(repository)


PaymentServiceDep = Annotated[PaymentService, Depends(get_payment_service)]
TariffServiceDep = Annotated[TariffService, Depends(get_tariff_service)]
WebhookServiceDep = Annotated[WebhookService, Depends(get_webhook_service)]
