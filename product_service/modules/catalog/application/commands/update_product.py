"""
UpdateProductCommand — command object cho use-case cập nhật sản phẩm
"""
from dataclasses import dataclass, field
from typing import Optional


@dataclass
class UpdateProductCommand:
    """Dữ liệu đầu vào để cập nhật một Product"""
    product_id: int
    name: Optional[str] = None
    slug: Optional[str] = None
    description: Optional[str] = None
    category_id: Optional[int] = None
    brand_id: Optional[int] = None
    product_type_id: Optional[int] = None
    attributes: Optional[dict] = None
    is_active: Optional[bool] = None
