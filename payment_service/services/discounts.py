from typing import Protocol


class DiscountStrategy(Protocol):
    def calculate(self, price: int) -> int: ...


class TenPercentDiscount:
    def calculate(self, price: int) -> int:
        # shortcut: fractional kopeck discounts round down; revisit if prices change.
        return price // 10
