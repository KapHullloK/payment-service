from datetime import datetime
from typing import Literal, Self

from email_validator import validate_email
from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

type PaymentStatus = Literal["pending", "succeeded", "failed", "refunded"]


class PaymentCreate(BaseModel):
    tariff_id: int = Field(gt=0, description="ID тарифа из списка /tariffs.")
    email: str = Field(
        pattern=r"^[^@\s]+@[^@\s]+\.[^@\s]+$",
        description="Email плательщика.",
    )
    method: Literal["card", "sbp", "installment"] = Field(
        description="Способ оплаты: карта, СБП или рассрочка."
    )
    installment_months: Literal[3, 6, 12] | None = Field(
        default=None,
        description="Срок рассрочки в месяцах; обязателен только для рассрочки.",
    )
    promo_code: str | None = Field(
        default=None,
        description="Промокод KVITTO10; регистр не имеет значения.",
    )

    @field_validator("email")
    @classmethod
    def validate_email_address(cls, value: str) -> str:
        validate_email(value, check_deliverability=False)
        return value

    @field_validator("promo_code")
    @classmethod
    def normalize_promo_code(cls, value: str | None) -> str | None:
        return value.upper() if value is not None else None

    @model_validator(mode="after")
    def validate_installment_months(self) -> Self:
        if (self.method == "installment") != (self.installment_months is not None):
            raise ValueError("installment_months is required only for installment")
        return self


class PaymentRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int = Field(description="ID платежа.")
    status: PaymentStatus = Field(description="Текущий статус платежа.")
    tariff_id: int = Field(description="ID оплачиваемого тарифа.")
    amount: int = Field(description="Сумма к оплате после скидки, в копейках.")
    discount: int = Field(description="Размер скидки в копейках.")
    method: Literal["card", "sbp", "installment"] = Field(
        description="Способ оплаты."
    )
    installment_months: int | None = Field(
        description="Срок рассрочки в месяцах или null."
    )
    schedule: list[int] | None = Field(
        description="Суммы платежей по месяцам в копейках или null."
    )
    email: str = Field(description="Email плательщика.")
    created_at: datetime = Field(description="Дата и время создания платежа.")
