from datetime import datetime

from sqlalchemy import BigInteger, CheckConstraint, DateTime, ForeignKey, Text, func
from sqlalchemy.dialects.postgresql import ARRAY
from sqlalchemy.orm import Mapped, mapped_column

from payment_service.core.db.models.base import Base


class Payment(Base):
    __tablename__ = "payments"
    __table_args__ = (
        CheckConstraint("amount >= 0", name="ck_payments_amount_nonnegative"),
        CheckConstraint("discount >= 0", name="ck_payments_discount_nonnegative"),
        CheckConstraint(
            "status IN ('pending', 'succeeded', 'failed', 'refunded')",
            name="ck_payments_status",
        ),
        CheckConstraint(
            "method IN ('card', 'sbp', 'installment')", name="ck_payments_method"
        ),
        CheckConstraint(
            "(method = 'installment' AND installment_months IN (3, 6, 12)) OR "
            "(method IN ('card', 'sbp') AND installment_months IS NULL)",
            name="ck_payments_installment_months",
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    status: Mapped[str] = mapped_column(Text, server_default="pending")
    tariff_id: Mapped[int] = mapped_column(ForeignKey("tariffs.id"))
    amount: Mapped[int] = mapped_column(BigInteger)
    discount: Mapped[int] = mapped_column(BigInteger)
    method: Mapped[str] = mapped_column(Text)
    installment_months: Mapped[int | None]
    schedule: Mapped[list[int] | None] = mapped_column(ARRAY(BigInteger))
    email: Mapped[str] = mapped_column(Text)
    idempotency_key: Mapped[str | None] = mapped_column(Text, unique=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
