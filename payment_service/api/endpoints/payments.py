from typing import Annotated

from fastapi import APIRouter, Header, HTTPException, Path, Query, Response
from fastapi.exceptions import RequestValidationError

from payment_service.api.dependencies import PaymentServiceDep
from payment_service.core.db.models import Payment
from payment_service.schemas.payments import PaymentCreate, PaymentRead, PaymentStatus
from payment_service.services.payments import TariffNotFoundError
from payment_service.services.pricing import UnknownPromoCodeError

router = APIRouter()


@router.post(
    "/payments",
    response_model=PaymentRead,
    status_code=201,
    summary="Создать платёж",
    description=(
        "Создаёт платёж в копейках. Повторный запрос с тем же Idempotency-Key "
        "возвращает существующий платёж с кодом 200."
    ),
)
async def create_payment_endpoint(
    payment: PaymentCreate,
    response: Response,
    service: PaymentServiceDep,
    idempotency_key: Annotated[
        str | None,
        Header(
            alias="Idempotency-Key",
            description="Возвращает существующий платёж при повторном запросе.",
        ),
    ] = None,
) -> Payment:
    try:
        result, created = await service.create_payment(payment, idempotency_key)
    except UnknownPromoCodeError as exc:
        raise RequestValidationError(
            [
                {
                    "type": "value_error",
                    "loc": ("body", "promo_code"),
                    "msg": f"Value error, {exc}",
                    "input": payment.promo_code,
                    "ctx": {"error": str(exc)},
                }
            ]
        ) from exc
    except TariffNotFoundError as exc:
        raise HTTPException(status_code=404, detail="Tariff not found") from exc
    if not created:
        response.status_code = 200
    return result


@router.get(
    "/payments",
    response_model=list[PaymentRead],
    summary="Получить список платежей",
    description=(
        "Возвращает все платежи с необязательной фильтрацией по email и статусу."
    ),
)
async def get_payments(
    service: PaymentServiceDep,
    email: Annotated[
        str | None, Query(description="Точное совпадение с email плательщика.")
    ] = None,
    status: Annotated[
        PaymentStatus | None, Query(description="Фильтр по статусу платежа.")
    ] = None,
) -> list[Payment]:
    return await service.list_payments(email, status)


@router.get(
    "/payments/{payment_id}",
    response_model=PaymentRead,
    summary="Получить платёж",
    description="Возвращает платёж по ID или код 404, если он не найден.",
)
async def get_payment_endpoint(
    payment_id: Annotated[int, Path(description="ID платежа.")],
    service: PaymentServiceDep,
) -> Payment:
    payment = await service.get_payment(payment_id)
    if payment is None:
        raise HTTPException(status_code=404, detail="Payment not found")
    return payment
