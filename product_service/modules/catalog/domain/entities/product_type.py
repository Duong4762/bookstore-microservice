"""
ProductType Entity — loại sản phẩm (e.g. Sách bìa cứng, Sách điện tử, Truyện tranh)
"""
from __future__ import annotations
from dataclasses import dataclass
from typing import Optional


@dataclass
class ProductType:
    """
    Entity phân loại kiểu sản phẩm.
    Kiểm soát những attribute nào cần thiết cho sản phẩm thuộc loại này.
    """
    id: Optional[int]
    name: str
    # e.g. ["author", "pages", "language", "isbn"] — attributes required for this type
    required_attributes: list = None

    def __post_init__(self):
        if self.required_attributes is None:
            self.required_attributes = []
        if not self.name or not self.name.strip():
            raise ValueError("ProductType name cannot be empty")

    def requires_attribute(self, attr_name: str) -> bool:
        return attr_name in self.required_attributes

    def __repr__(self) -> str:
        return f"ProductType(id={self.id}, name={self.name!r})"
