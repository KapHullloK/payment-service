import asyncio
import hashlib
import hmac
import json

import pytest
from httpx import ASGITransport, AsyncClient, Response

from payment_service.api.dependencies import get_webhook_service
from payment_service.core.config import get_settings
from payment_service.main import app


def sign(body: bytes) -> str:
    return hmac.new(b"test-secret", body, hashlib.sha256).hexdigest()


async def send_webhook(
        client: AsyncClient, body: bytes, signature: str | None
) -> Response:
    headers = {"Content-Type": "application/json"}
    if signature is not None:
        headers["X-Signature"] = signature
    return await client.post("/webhooks/bank", content=body, headers=headers)


async def create_payment(client: AsyncClient) -> int:
    tariff_id = (await client.get("/tariffs")).json()[0]["id"]
    response = await client.post(
        "/payments",
        json={"tariff_id": tariff_id, "email": "payer@example.com", "method": "card"},
    )
    assert response.status_code == 201
    return response.json()["id"]


def notification(payment_id: int, status: str) -> bytes:
    return json.dumps({"payment_id": payment_id, "status": status}).encode()


@pytest.mark.asyncio
async def test_non_ascii_signature_returns_401(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("WEBHOOK_SECRET", "test-secret")
    monkeypatch.setenv("DATABASE_PASSWORD", "test-password")
    get_settings.cache_clear()
    app.dependency_overrides[get_webhook_service] = lambda: object()
    try:
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            response = await client.post(
                "/webhooks/bank", content=b"{}", headers={b"X-Signature": b"\xff"}
            )
            assert response.status_code == 401
    finally:
        app.dependency_overrides.clear()
        get_settings.cache_clear()


@pytest.mark.asyncio
async def test_webhook_transitions(database_url: str) -> None:
    async with app.router.lifespan_context(app):
        async with AsyncClient(
                transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            paths = {
                "pending": (),
                "succeeded": ("succeeded",),
                "failed": ("failed",),
                "refunded": ("succeeded", "refunded"),
            }
            allowed = {
                ("pending", "succeeded"),
                ("pending", "failed"),
                ("succeeded", "refunded"),
            }
            for current, setup_statuses in paths.items():
                for target in paths:
                    payment_id = await create_payment(client)
                    for status in setup_statuses:
                        setup_body = notification(payment_id, status)
                        setup_result = await send_webhook(
                            client, setup_body, sign(setup_body)
                        )
                        assert setup_result.status_code == 200
                        assert setup_result.json() == {"result": "ok"}

                    body = notification(payment_id, target)
                    result = await send_webhook(client, body, sign(body))
                    valid = (current, target) in allowed
                    assert result.status_code == (200 if valid else 409), (
                        current,
                        target,
                        result.text,
                    )
                    assert result.json() == (
                        {"result": "ok"} if valid else {"error": "invalid_transition"}
                    )
                    assert (await client.get(f"/payments/{payment_id}")).json()[
                               "status"
                           ] == (target if valid else current)

            missing = notification(999999, "succeeded")
            result = await send_webhook(client, missing, sign(missing))
            assert result.status_code == 404
            assert result.json() == {"detail": "Payment not found"}

            concurrent_id = await create_payment(client)
            statuses = ["succeeded", "failed"]
            bodies = [notification(concurrent_id, status) for status in statuses]
            responses = await asyncio.gather(
                *(send_webhook(client, body, sign(body)) for body in bodies)
            )
            assert sorted(response.status_code for response in responses) == [200, 409]
            assert {
                       response.status_code: response.json() for response in responses
                   } == {
                       200: {"result": "ok"},
                       409: {"error": "invalid_transition"},
                   }
            winner = next(i for i, r in enumerate(responses) if r.status_code == 200)
            assert (await client.get(f"/payments/{concurrent_id}")).json()[
                       "status"
                   ] == statuses[winner]


@pytest.mark.asyncio
async def test_webhook_signature_and_validation(database_url: str) -> None:
    async with app.router.lifespan_context(app):
        async with AsyncClient(
                transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            payment_id = await create_payment(client)
            body = notification(payment_id, "succeeded")
            for rejected_body, signature in (
                    (body, None),
                    (body, "0" * 64),
                    (body.replace(b"succeeded", b"failed"), sign(body)),
                    (b"not json", "0" * 64),
            ):
                result = await send_webhook(client, rejected_body, signature)
                assert result.status_code == 401
                assert (await client.get(f"/payments/{payment_id}")).json()[
                           "status"
                       ] == "pending"

            for invalid_body in (
                    b"not json",
                    b"\xff",
                    notification(payment_id, "unknown"),
            ):
                result = await send_webhook(client, invalid_body, sign(invalid_body))
                assert result.status_code == 422
                assert isinstance(result.json()["detail"], list)
                assert (await client.get(f"/payments/{payment_id}")).json()[
                           "status"
                       ] == "pending"

            raw_body = (
                f'{{ "payment_id": {payment_id}, "status": "succeeded" }}'.encode()
            )
            result = await send_webhook(client, raw_body, sign(raw_body))
            assert result.status_code == 200
            assert result.json() == {"result": "ok"}
            assert (await client.get(f"/payments/{payment_id}")).json()["status"] == (
                "succeeded"
            )
