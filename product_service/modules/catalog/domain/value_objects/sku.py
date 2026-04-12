"""
SKU (Stock Keeping Unit) Value Object
"""
from __future__ import annotations
import re
from dataclasses import dataclass

from shared.exceptions import InvalidSKU

# Allowed format: ALPHANUMERIC-ALPHANUMERIC  e.g. BOOK-0001, HAPO-0042-HB
SKU_PATTERN = re.compile(r'^[A-Z0-9]{2,8}(-[A-Z0-9]{1,8}){1,3}$')


@dataclass(frozen=True)
class SKU:
    """
    Value Object đại diện cho mã SKU của một variant sản phẩm.
    """
    value: str

    def __post_init__(self):
        normalized = self.value.upper().strip()
        object.__setattr__(self, 'value', normalized)
        if not SKU_PATTERN.match(normalized):
            raise InvalidSKU(
                f"Invalid SKU format: '{normalized}'. "
                f"Expected pattern like 'BOOK-0001' or 'HARP-0001-HB'"
            )

    def __str__(self) -> str:
        return self.value

    def __repr__(self) -> str:
        return f"SKU({self.value!r})"

    @classmethod
    def of(cls, value: str) -> SKU:
        return cls(value)
