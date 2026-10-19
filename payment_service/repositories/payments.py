from sqlalchemy import select, update
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from payment_service.core.db.models import Payment
from payment_service.schemas.payments import PaymentStatus


class PaymentRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get(self, payment_id: int) -> Payment | None:
        return await self.session.get(Payment, payment_id)

    async def get_by_idempotency_key(self, idempotency_key: str) -> Payment | None:
        return await self.session.scalar(
            select(Payment).where(Payment.idempotency_key == idempotency_key)
        )

    async def create(
        self,
        *,
        tariff_id: int,
        amount: int,
        discount: int,
        method: str,
        installment_months: int | None,
        schedule: list[int] | None,
        email: str,
        idempotency_key: str | None,
    ) -> tuple[Payment, bool]:
        statement = insert(Payment).values(
            tariff_id=tariff_id,
            amount=amount,
            discount=discount,
            method=method,
            installment_months=installment_months,
            schedule=schedule,
            email=email,
            idempotency_key=idempotency_key,
        )
        if idempotency_key is not None:
            statement = statement.on_conflict_do_nothing(
                index_elements=[Payment.idempotency_key]
            )
        created = await self.session.scalar(statement.returning(Payment))
        await self.session.commit()
        if created is not None:
            return created, True
        if idempotency_key is None:
            raise RuntimeError("Payment insert returned no row")
        existing = await self.get_by_idempotency_key(idempotency_key)
        if existing is None:
            raise RuntimeError("Conflicting payment was not found")
        return existing, False

    async def list(
        self, email: str | None, status: PaymentStatus | None
    ) -> list[Payment]:
        statement = select(Payment)
        if email is not None:
            statement = statement.where(Payment.email == email)
        if status is not None:
            statement = statement.where(Payment.status == status)
        result = await self.session.scalars(statement.order_by(Payment.id))
        return list(result.all())

    async def update_status_if_current(
        self,
        payment_id: int,
        status: PaymentStatus,
        allowed_sources: tuple[str, ...],
    ) -> bool:
        changed_id = await self.session.scalar(
            update(Payment)
            .where(
                Payment.id == payment_id,
                Payment.status.in_(allowed_sources),
            )
            .values(status=status)
            .returning(Payment.id)
        )
        if changed_id is None:
            return False
        await self.session.commit()
        return True
