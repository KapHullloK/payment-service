import pytest
from pydantic import ValidationError

from payment_service.schemas import PaymentCreate
from payment_service.services.pricing import PricingService


@pytest.mark.parametrize(
    ("promo_code", "amount", "discount"),
    [
        (None, 1990000, 0),
        ("KVITTO10", 1791000, 199000),
        ("kvitto10", 1791000, 199000),
    ],
)
def test_payment_amount(promo_code: str | None, amount: int, discount: int) -> None:
    assert PricingService().calculate_amount(1990000, promo_code) == (amount, discount)


def test_discount_rounds_down_to_kopecks() -> None:
    assert PricingService().calculate_amount(101, "KVITTO10") == (91, 10)


@pytest.mark.parametrize("months", [3, 6, 12])
def test_installment_schedule(months: int) -> None:
    amount = 1990000
    schedule = PricingService().installment_schedule(amount, months)
    assert len(schedule) == months
    assert sum(schedule) == amount
    assert max(schedule) - min(schedule) <= 1
    if months == 3:
        assert schedule == [663334, 663333, 663333]


def test_invalid_pricing_inputs() -> None:
    with pytest.raises(ValueError):
        PricingService().calculate_amount(1990000, "UNKNOWN")
    with pytest.raises(ValueError):
        PricingService().installment_schedule(1990000, 0)


def test_new_discount_strategy() -> None:
    class FixedDiscount:
        def calculate(self, price: int) -> int:
            return 250

    service = PricingService({"FIXED": FixedDiscount()})
    assert service.normalize_promo_code("fixed") == "FIXED"
    assert service.calculate_amount(1000, "fixed") == (750, 250)


def test_payment_input_validation() -> None:
    payment = PaymentCreate.model_validate(
        {
            "tariff_id": 1,
            "email": "Student@Example.com",
            "method": "installment",
            "installment_months": 6,
            "promo_code": "kvitto10",
        }
    )
    assert payment.promo_code == "KVITTO10"
    assert payment.email == "Student@Example.com"

    for changes in (
            {"method": "cash"},
            {"installment_months": 2},
            {"installment_months": None},
            {"email": "invalid"},
            {"email": "a\x00b@example.com"},
            {"email": "a..b@example.com"},
    ):
        with pytest.raises(ValidationError):
            PaymentCreate.model_validate({**payment.model_dump(), **changes})

    with pytest.raises(ValidationError):
        PaymentCreate.model_validate({**payment.model_dump(), "method": "card"})
