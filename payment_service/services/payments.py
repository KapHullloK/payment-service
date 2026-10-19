from payment_service.core.db.models import Payment
from payment_service.repositories.payments import PaymentRepository
from payment_service.repositories.tariffs import TariffRepository
from payment_service.schemas.payments import PaymentCreate, PaymentStatus
from payment_service.services.pricing import PricingService


class TariffNotFoundError(Exception):
    pass


class PaymentService:
    def __init__(
        self,
        payment_repository: PaymentRepository,
        tariff_repository: TariffRepository,
        pricing_service: PricingService,
    ) -> None:
        self.payment_repository = payment_repository
        self.tariff_repository = tariff_repository
        self.pricing_service = pricing_service

    async def create_payment(
        self, request: PaymentCreate, idempotency_key: str | None
    ) -> tuple[Payment, bool]:
        self.pricing_service.normalize_promo_code(request.promo_code)
        if idempotency_key is not None:
            existing = await self.payment_repository.get_by_idempotency_key(
                idempotency_key
            )
            if existing is not None:
                return existing, False

        tariff = await self.tariff_repository.get(request.tariff_id)
        if tariff is None:
            raise TariffNotFoundError

        amount, discount = self.pricing_service.calculate_amount(
            tariff.price, request.promo_code
        )
        months = request.installment_months
        schedule = (
            self.pricing_service.installment_schedule(amount, months)
            if months is not None
            else None
        )
        return await self.payment_repository.create(
            tariff_id=tariff.id,
            amount=amount,
            discount=discount,
            method=request.method,
            installment_months=months,
            schedule=schedule,
            email=request.email,
            idempotency_key=idempotency_key,
        )

    async def list_payments(
        self, email: str | None, status: PaymentStatus | None
    ) -> list[Payment]:
        return await self.payment_repository.list(email, status)

    async def get_payment(self, payment_id: int) -> Payment | None:
        return await self.payment_repository.get(payment_id)
