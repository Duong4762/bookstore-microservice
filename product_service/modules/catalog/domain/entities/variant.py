"""
Variant Entity — một biến thể cụ thể của sản phẩm (size, color, edition...)
"""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import Optional

from modules.catalog.domain.value_objects import Money, SKU, Attributes
from shared.exceptions import InsufficientStock


@dataclass
class Variant:
    """
    Entity đại diện cho một biến thể cụ thể của sản phẩm.
    Ví dụ: Sách "Harry Potter" có thể có variant bìa cứng và bìa mềm,
    mỗi variant có SKU riêng, giá riêng và tồn kho riêng.
    """
    id: Optional[int]
    product_id: int
    sku: SKU
    price: Money
    stock: int = 0
    attributes: Attributes = field(default_factory=Attributes.empty)
    is_active: bool = True
    cover_image_url: Optional[str] = None

    def __post_init__(self):
        if self.stock < 0:
            raise ValueError("Stock cannot be negative")
        if not isinstance(self.sku, SKU):
            self.sku = SKU(self.sku)
        if not isinstance(self.price, Money):
            self.price = Money.of(self.price)

    # ── Domain behaviours ──────────────────────────────────────────────────

    @property
    def in_stock(self) -> bool:
        return self.stock > 0 and self.is_active

    def check_availability(self, requested_qty: int) -> tuple[bool, str]:
        """
        Kiểm tra xem có đủ hàng không.
        Returns: (available: bool, message: str)
        """
        if not self.is_active:
            return False, "Sản phẩm hiện không khả dụng"
        if self.stock < requested_qty:
            return False, f"Chỉ còn {self.stock} sản phẩm trong kho"
        return True, "Sản phẩm có sẵn"

    def reduce_stock(self, qty: int) -> None:
        """Giảm tồn kho sau khi đặt hàng thành công"""
        if self.stock < qty:
            raise InsufficientStock(available=self.stock, requested=qty)
        self.stock -= qty

    def restock(self, qty: int) -> None:
        """Nhập thêm hàng"""
        if qty <= 0:
            raise ValueError("Restock quantity must be positive")
        self.stock += qty

    def __repr__(self) -> str:
        return (
            f"Variant(id={self.id}, sku={self.sku}, "
            f"price={self.price}, stock={self.stock})"
        )
