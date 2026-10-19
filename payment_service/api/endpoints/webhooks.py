import hashlib
import hmac

from fastapi import APIRouter, Header, HTTPException, Request, Response
from fastapi.exceptions import RequestValidationError
from pydantic import ValidationError

from payment_service.api.dependencies import WebhookServiceDep
from payment_service.core.config import get_settings
from payment_service.schemas.webhooks import BankWebhook
from payment_service.services.webhooks import TransitionResult

router = APIRouter()


@router.post(
    "/webhooks/bank",
    summary="Обработать уведомление банка",
    description=(
        "Проверяет X-Signature как HMAC-SHA256 исходного тела запроса и обновляет "
        "статус платежа, если переход разрешён."
    ),
    openapi_extra={
        "requestBody": {
            "required": True,
            "content": {
                "application/json": {
                    "schema": BankWebhook.model_json_schema(
                        ref_template="#/components/schemas/{model}"
                    )
                }
            },
        }
    },
)
async def bank_webhook(
    request: Request,
    response: Response,
    service: WebhookServiceDep,
    signature: str | None = Header(
        default=None,
        alias="X-Signature",
        description="Шестнадцатеричная HMAC-SHA256 подпись исходного тела запроса.",
    ),
) -> dict[str, str]:
    body = await request.body()
    expected = hmac.new(
        get_settings().app.webhook_secret.encode(), body, hashlib.sha256
    ).hexdigest()
    if (
        signature is None
        or not signature.isascii()
        or not hmac.compare_digest(signature, expected)
    ):
        raise HTTPException(status_code=401, detail="Invalid signature")

    try:
        notification = BankWebhook.model_validate_json(body)
    except ValidationError as exc:
        errors = []
        for error in exc.errors():
            error["loc"] = ("body", *error["loc"])
            if isinstance(error.get("input"), bytes):
                error["input"] = error["input"].decode("utf-8", errors="replace")
            errors.append(error)
        raise RequestValidationError(errors, body=body) from exc

    result = await service.process_bank_webhook(notification)
    if result is TransitionResult.NOT_FOUND:
        raise HTTPException(status_code=404, detail="Payment not found")
    if result is TransitionResult.INVALID_TRANSITION:
        response.status_code = 409
        return {"error": "invalid_transition"}
    return {"result": "ok"}
