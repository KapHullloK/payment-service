import asyncio
from datetime import datetime

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import update

from payment_service.api.dependencies import get_pricing_service
from payment_service.core.db.models import Payment
from payment_service.core.db.session import get_engine
from payment_service.main import app
from payment_service.services.pricing import PricingService


@pytest.mark.asyncio
async def test_tariffs_and_payment_endpoints(database_url: str) -> None:
    async with app.router.lifespan_context(app):
        async with AsyncClient(
                transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            tariffs_response = await client.get("/tariffs")
            assert tariffs_response.status_code == 200
            tariffs = tariffs_response.json()
            assert [(tariff["title"], tariff["price"]) for tariff in tariffs] == [
                ("basic", 990000),
                ("standard", 1990000),
                ("premium", 2990000),
            ]
            assert all(set(tariff) == {"id", "title", "price"} for tariff in tariffs)
            basic_id, standard_id = tariffs[0]["id"], tariffs[1]["id"]

            first_body = {
                "tariff_id": standard_id,
                "email": "Alice@Example.com",
                "method": "card",
                "promo_code": "kvitto10",
            }
            first_response = await client.post(
                "/payments", json=first_body, headers={"Idempotency-Key": "same-key"}
            )
            assert first_response.status_code == 201
            first = first_response.json()
            assert set(first) == {
                "id",
                "status",
                "tariff_id",
                "amount",
                "discount",
                "method",
                "installment_months",
                "schedule",
                "email",
                "created_at",
            }
            assert first["status"] == "pending"
            assert first["tariff_id"] == standard_id
            assert (first["amount"], first["discount"]) == (1791000, 199000)
            assert first["installment_months"] is None
            assert first["schedule"] is None
            assert first["email"] == "Alice@Example.com"
            assert datetime.fromisoformat(first["created_at"]).tzinfo is not None

            second_response = await client.post(
                "/payments",
                json={
                    "tariff_id": standard_id,
                    "email": "bob@example.com",
                    "method": "installment",
                    "installment_months": 3,
                },
            )
            assert second_response.status_code == 201
            second = second_response.json()
            assert second["amount"] == 1990000
            assert second["discount"] == 0
            assert second["schedule"] == [663334, 663333, 663333]

            third_response = await client.post(
                "/payments",
                json={
                    "tariff_id": basic_id,
                    "email": "Alice@Example.com",
                    "method": "sbp",
                },
            )
            assert third_response.status_code == 201
            third = third_response.json()
            assert third["amount"] == 990000

            async with get_engine().begin() as connection:
                await connection.execute(
                    update(Payment)
                    .where(Payment.id == first["id"])
                    .values(status="succeeded")
                )

            repeat_response = await client.post(
                "/payments",
                json={
                    "tariff_id": basic_id,
                    "email": "other@example.com",
                    "method": "sbp",
                },
                headers={"Idempotency-Key": "same-key"},
            )
            assert repeat_response.status_code == 200
            assert repeat_response.json() == {**first, "status": "succeeded"}
            assert (await client.get(f"/payments/{first['id']}")).json() == {
                **first,
                "status": "succeeded",
            }
            missing_payment = await client.get("/payments/999999")
            assert missing_payment.status_code == 404
            assert missing_payment.json() == {"detail": "Payment not found"}

            all_response = await client.get("/payments")
            assert all_response.status_code == 200
            assert [item["id"] for item in all_response.json()] == [
                first["id"],
                second["id"],
                third["id"],
            ]
            assert [
                       item["id"]
                       for item in (
                    await client.get("/payments", params={"email": "Alice@Example.com"})
                ).json()
                   ] == [first["id"], third["id"]]
            assert [
                       item["id"]
                       for item in (
                    await client.get("/payments", params={"status": "succeeded"})
                ).json()
                   ] == [first["id"]]
            assert [
                       item["id"]
                       for item in (
                    await client.get(
                        "/payments",
                        params={"email": "Alice@Example.com", "status": "succeeded"},
                    )
                ).json()
                   ] == [first["id"]]
            empty_response = await client.get(
                "/payments", params={"email": "alice@example.com"}
            )
            assert empty_response.status_code == 200
            assert empty_response.json() == []
            assert (
                       await client.get("/payments", params={"status": "failed"})
                   ).json() == []
            invalid_status = await client.get("/payments", params={"status": "unknown"})
            assert invalid_status.status_code == 422
            assert isinstance(invalid_status.json()["detail"], list)

            invalid_promo = await client.post(
                "/payments",
                json={**first_body, "promo_code": "bad"},
                headers={"Idempotency-Key": "same-key"},
            )
            assert invalid_promo.status_code == 422
            assert isinstance(invalid_promo.json()["detail"], list)
            missing_tariff = await client.post(
                "/payments", json={**first_body, "tariff_id": 999999}
            )
            assert missing_tariff.status_code == 404
            assert missing_tariff.json() == {"detail": "Tariff not found"}


@pytest.mark.asyncio
async def test_custom_discount_uses_injected_pricing(database_url: str) -> None:
    class FixedDiscount:
        def calculate(self, price: int) -> int:
            return 250

    app.dependency_overrides[get_pricing_service] = lambda: PricingService(
        {"FIXED": FixedDiscount()}
    )
    try:
        async with app.router.lifespan_context(app):
            async with AsyncClient(
                transport=ASGITransport(app=app), base_url="http://test"
            ) as client:
                tariff_id = (await client.get("/tariffs")).json()[0]["id"]
                body = {
                    "tariff_id": tariff_id,
                    "email": "student@example.com",
                    "method": "card",
                }
                created = await client.post(
                    "/payments", json={**body, "promo_code": "fixed"}
                )
                assert created.status_code == 201
                assert created.json()["discount"] == 250
                assert created.json()["amount"] == 990000 - 250

                invalid = await client.post(
                    "/payments", json={**body, "promo_code": "unknown"}
                )
                assert invalid.status_code == 422
                assert invalid.json()["detail"][0]["loc"] == ["body", "promo_code"]
    finally:
        app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_concurrent_idempotency(database_url: str) -> None:
    async with app.router.lifespan_context(app):
        async with AsyncClient(
                transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            tariff_id = (await client.get("/tariffs")).json()[0]["id"]
            body = {
                "tariff_id": tariff_id,
                "email": "alice@example.com",
                "method": "card",
            }
            responses = await asyncio.gather(
                *(
                    client.post(
                        "/payments", json=body, headers={"Idempotency-Key": "race-key"}
                    )
                    for _ in range(4)
                )
            )
            assert sorted(response.status_code for response in responses) == [
                200,
                200,
                200,
                201,
            ]
            assert len({response.json()["id"] for response in responses}) == 1
            assert len((await client.get("/payments")).json()) == 1
