from enum import StrEnum

from payment_service.repositories.payments import PaymentRepository
from payment_service.schemas.payments import PaymentStatus
from payment_service.schemas.webhooks import BankWebhook


class TransitionResult(StrEnum):
    UPDATED = "updated"
    INVALID_TRANSITION = "invalid_transition"
    NOT_FOUND = "not_found"


ALLOWED_SOURCES: dict[PaymentStatus, tuple[str, ...]] = {
    "succeeded": ("pending",),
    "failed": ("pending",),
    "refunded": ("succeeded",),
}


class WebhookService:
    def __init__(self, repository: PaymentRepository) -> None:
        self.repository = repository

    async def process_bank_webhook(self, notification: BankWebhook) -> TransitionResult:
        allowed_sources = ALLOWED_SOURCES.get(notification.status, ())
        updated = await self.repository.update_status_if_current(
            notification.payment_id,
            notification.status,
            allowed_sources,
        )
        if updated:
            return TransitionResult.UPDATED
        if await self.repository.get(notification.payment_id) is None:
            return TransitionResult.NOT_FOUND
        return TransitionResult.INVALID_TRANSITION
