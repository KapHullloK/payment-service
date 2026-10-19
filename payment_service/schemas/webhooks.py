from pydantic import BaseModel, Field

from payment_service.schemas.payments import PaymentStatus


class BankWebhook(BaseModel):
    payment_id: int = Field(gt=0, description="ID платежа, статус которого меняется.")
    status: PaymentStatus = Field(description="Новый статус платежа.")
