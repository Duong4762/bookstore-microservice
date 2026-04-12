"""
Product Entity — Aggregate Root of the catalog bounded context
"""
from __future__ import annotations
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional, List

from modules.catalog.domain.value_objects import Attributes


@dataclass
class Product:
    """
    Aggregate Root: Product là trung tâm của bounded context catalog.
    Mọi thay đổi đến variants đều đi qua Product.

    Ví dụ sách: name="Đắc Nhân Tâm", author ở trong attributes.
    """
    id: Optional[int]
    name: str
    slug: str
    description: str
    category_id: int
    brand_id: int
    product_type_id: int
    attributes: Attributes = field(default_factory=Attributes.empty)
    is_active: bool = True
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    def __post_init__(self):
        if not self.name or not self.name.strip():
            raise ValueError("Product name cannot be empty")
        if not self.slug or not self.slug.strip():
            raise ValueError("Product slug cannot be empty")
        if self.category_id <= 0:
            raise ValueError("category_id must be positive")
        if self.brand_id <= 0:
            raise ValueError("brand_id must be positive")

    # ── Domain behaviours ──────────────────────────────────────────────────

    def deactivate(self) -> None:
        """Ngừng kinh doanh sản phẩm này"""
        self.is_active = False

    def activate(self) -> None:
        """Kích hoạt lại sản phẩm"""
        self.is_active = True

    def update_attribute(self, key: str, value) -> None:
        """Cập nhật một thuộc tính của sản phẩm"""
        self.attributes = self.attributes.with_attribute(key, value)

    def get_attribute(self, key: str, default=None):
        return self.attributes.get(key, default)

    # Convenience helpers for book-specific attributes
    @property
    def author(self) -> Optional[str]:
        return self.attributes.get('author')

    @property
    def isbn(self) -> Optional[str]:
        return self.attributes.get('isbn')

    @property
    def language(self) -> str:
        return self.attributes.get('language', 'Vietnamese')

    @property
    def pages(self) -> Optional[int]:
        return self.attributes.get('pages')

    @property
    def publication_year(self) -> Optional[int]:
        return self.attributes.get('publication_year')

    def __repr__(self) -> str:
        return f"Product(id={self.id}, name={self.name!r}, active={self.is_active})"
