"""
CreateVariantCommand — command object cho use-case tạo variant mới
"""
from dataclasses import dataclass, field
from typing import Optional
from decimal import Decimal


@dataclass
class CreateVariantCommand:
    """Dữ liệu đầu vào để tạo một Variant"""
    product_id: int
    sku: str
    price: Decimal
    stock: int = 0
    attributes: dict = field(default_factory=dict)
    cover_image_url: Optional[str] = None
    is_active: bool = True
