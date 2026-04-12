"""
CreateProductCommand — command object cho use-case tạo sản phẩm mới
"""
from dataclasses import dataclass, field
from typing import Optional


@dataclass
class CreateProductCommand:
    """Dữ liệu đầu vào để tạo một Product mới"""
    name: str
    slug: str
    description: str
    category_id: int
    brand_id: int
    product_type_id: int
    attributes: dict = field(default_factory=dict)
    is_active: bool = True
