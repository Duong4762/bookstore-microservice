"""UpdateVariantCommand — cập nhật biến thể."""
from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from typing import Optional


@dataclass
class UpdateVariantCommand:
    variant_id: int
    product_id: int
    sku: Optional[str] = None
    price: Optional[Decimal] = None
    stock: Optional[int] = None
    cover_image_url: Optional[str] = None
    is_active: Optional[bool] = None
