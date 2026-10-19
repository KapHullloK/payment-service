from collections.abc import Mapping

from payment_service.services.discounts import DiscountStrategy, TenPercentDiscount

DEFAULT_DISCOUNTS: Mapping[str, DiscountStrategy] = {
    "KVITTO10": TenPercentDiscount(),
}


class UnknownPromoCodeError(ValueError):
    pass


class PricingService:
    def __init__(self, discounts: Mapping[str, DiscountStrategy] | None = None) -> None:
        self.discounts = DEFAULT_DISCOUNTS if discounts is None else discounts

    def normalize_promo_code(self, promo_code: str | None) -> str | None:
        if promo_code is None:
            return None
        code = promo_code.upper()
        if code not in self.discounts:
            raise UnknownPromoCodeError("Unknown promo code")
        return code

    def calculate_amount(self, price: int, promo_code: str | None) -> tuple[int, int]:
        code = self.normalize_promo_code(promo_code)
        discount = self.discounts[code].calculate(price) if code is not None else 0
        return price - discount, discount

    def installment_schedule(self, amount: int, months: int) -> list[int]:
        if months not in (3, 6, 12):
            raise ValueError("Installment months must be 3, 6, or 12")
        base, remainder = divmod(amount, months)
        return [base + (index < remainder) for index in range(months)]
