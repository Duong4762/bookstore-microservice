"""
Money Value Object — immutable, encapsulates amount + currency
"""
from __future__ import annotations
from dataclasses import dataclass
from decimal import Decimal, InvalidOperation

from shared.exceptions import InvalidPrice


@dataclass(frozen=True)
class Money:
    """
    Value Object đại diện cho một số tiền.
    Frozen = immutable (không thể thay đổi sau khi tạo).
    """
    amount: Decimal
    currency: str = "VND"

    def __post_init__(self):
        if not isinstance(self.amount, Decimal):
            object.__setattr__(self, 'amount', Decimal(str(self.amount)))
        if self.amount < Decimal('0'):
            raise InvalidPrice(f"Price cannot be negative: {self.amount}")

    def __add__(self, other: Money) -> Money:
        if self.currency != other.currency:
            raise ValueError(f"Cannot add {self.currency} and {other.currency}")
        return Money(self.amount + other.amount, self.currency)

    def __sub__(self, other: Money) -> Money:
        if self.currency != other.currency:
            raise ValueError(f"Cannot subtract {self.currency} and {other.currency}")
        result = self.amount - other.amount
        if result < Decimal('0'):
            raise InvalidPrice("Result cannot be negative")
        return Money(result, self.currency)

    def __mul__(self, factor: int | float | Decimal) -> Money:
        return Money(self.amount * Decimal(str(factor)), self.currency)

    def __repr__(self) -> str:
        return f"{self.amount:,.0f} {self.currency}"

    @classmethod
    def of(cls, amount: int | float | str | Decimal, currency: str = "VND") -> Money:
        """Factory method"""
        try:
            return cls(Decimal(str(amount)), currency)
        except InvalidOperation:
            raise InvalidPrice(f"Invalid price value: {amount}")

    @property
    def is_free(self) -> bool:
        return self.amount == Decimal('0')
