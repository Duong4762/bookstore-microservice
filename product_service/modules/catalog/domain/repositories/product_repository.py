"""
Abstract Product Repository — Domain interface (port)
Infrastructure will provide the concrete implementation (adapter).
"""
from __future__ import annotations
from abc import ABC, abstractmethod
from typing import Optional, List

from modules.catalog.domain.entities import Product, Variant, Category


class AbstractProductRepository(ABC):
    """
    Port: interface mà application layer sử dụng.
    Infrastructure layer cài đặt concrete class kế thừa từ đây.
    """

    # ── Product operations ─────────────────────────────────────────────────

    @abstractmethod
    def get_product_by_id(self, product_id: int) -> Optional[Product]:
        ...

    @abstractmethod
    def get_product_by_slug(self, slug: str) -> Optional[Product]:
        ...

    @abstractmethod
    def list_products(self, filters: dict = None) -> List[Product]:
        ...

    @abstractmethod
    def save_product(self, product: Product) -> Product:
        """Create or update a product"""
        ...

    @abstractmethod
    def delete_product(self, product_id: int) -> bool:
        ...

    # ── Variant operations ─────────────────────────────────────────────────

    @abstractmethod
    def get_variant_by_id(self, variant_id: int) -> Optional[Variant]:
        ...

    @abstractmethod
    def get_variants_by_product(self, product_id: int) -> List[Variant]:
        ...

    @abstractmethod
    def save_variant(self, variant: Variant) -> Variant:
        ...

    @abstractmethod
    def delete_variant(self, variant_id: int) -> bool:
        ...

    # ── Category operations ────────────────────────────────────────────────

    @abstractmethod
    def get_category_by_id(self, category_id: int) -> Optional[Category]:
        ...

    @abstractmethod
    def list_categories(self) -> List[Category]:
        ...

    @abstractmethod
    def save_category(self, category: Category) -> Category:
        ...
