"""
ProductApplicationService — orchestrates all product-related use-cases.
This is the heart of the application layer.
"""
from __future__ import annotations
from typing import List, Optional

from modules.catalog.domain.entities import Product, Variant, Category
from modules.catalog.domain.value_objects import Money, SKU, Attributes
from modules.catalog.domain.repositories.product_repository import AbstractProductRepository
from modules.catalog.application.commands.create_product import CreateProductCommand
from modules.catalog.application.commands.update_product import UpdateProductCommand
from modules.catalog.application.commands.create_variant import CreateVariantCommand
from modules.catalog.application.queries.get_product import (
    GetProductQuery, ListProductsQuery
)
from shared.exceptions import ProductNotFound, VariantNotFound


class ProductApplicationService:
    """
    Application Service: điều phối các use-cases.
    - Nhận commands/queries từ presentation layer
    - Giao tiếp với domain qua repository interface
    - Không chứa business rules (business rules ở domain entities)
    """

    def __init__(self, repository: AbstractProductRepository):
        self._repo = repository

    # ── Product use-cases ──────────────────────────────────────────────────

    def create_product(self, cmd: CreateProductCommand) -> Product:
        """Use-case: tạo sản phẩm mới"""
        product = Product(
            id=None,
            name=cmd.name,
            slug=cmd.slug,
            description=cmd.description,
            category_id=cmd.category_id,
            brand_id=cmd.brand_id,
            product_type_id=cmd.product_type_id,
            attributes=Attributes(cmd.attributes),
            is_active=cmd.is_active,
        )
        return self._repo.save_product(product)

    def get_product(self, query: GetProductQuery) -> Product:
        """Use-case: lấy chi tiết một sản phẩm"""
        product = self._repo.get_product_by_id(query.product_id)
        if product is None:
            raise ProductNotFound(query.product_id)
        return product

    def list_products(self, query: ListProductsQuery) -> List[Product]:
        """Use-case: lấy danh sách sản phẩm với filter"""
        filters = {}
        if query.search:
            filters['search'] = query.search
        if query.category_id:
            filters['category_id'] = query.category_id
        if query.brand_id:
            filters['brand_id'] = query.brand_id
        if query.min_price is not None:
            filters['min_price'] = query.min_price
        if query.max_price is not None:
            filters['max_price'] = query.max_price
        if query.in_stock_only:
            filters['in_stock_only'] = True
        if query.is_active_only:
            filters['is_active'] = True
        filters['ordering'] = query.ordering
        return self._repo.list_products(filters)

    def update_product(self, cmd: UpdateProductCommand) -> Product:
        """Use-case: cập nhật thông tin sản phẩm"""
        product = self._repo.get_product_by_id(cmd.product_id)
        if product is None:
            raise ProductNotFound(cmd.product_id)

        if cmd.name is not None:
            product.name = cmd.name
        if cmd.slug is not None:
            product.slug = cmd.slug
        if cmd.description is not None:
            product.description = cmd.description
        if cmd.category_id is not None:
            product.category_id = cmd.category_id
        if cmd.brand_id is not None:
            product.brand_id = cmd.brand_id
        if cmd.product_type_id is not None:
            product.product_type_id = cmd.product_type_id
        if cmd.attributes is not None:
            product.attributes = Attributes(cmd.attributes)
        if cmd.is_active is not None:
            product.is_active = cmd.is_active

        return self._repo.save_product(product)

    def delete_product(self, product_id: int) -> bool:
        """Use-case: xóa sản phẩm"""
        if self._repo.get_product_by_id(product_id) is None:
            raise ProductNotFound(product_id)
        return self._repo.delete_product(product_id)

    # ── Variant use-cases ──────────────────────────────────────────────────

    def create_variant(self, cmd: CreateVariantCommand) -> Variant:
        """Use-case: tạo variant cho sản phẩm"""
        # Validate product exists
        product = self._repo.get_product_by_id(cmd.product_id)
        if product is None:
            raise ProductNotFound(cmd.product_id)

        variant = Variant(
            id=None,
            product_id=cmd.product_id,
            sku=SKU(cmd.sku),
            price=Money.of(cmd.price),
            stock=cmd.stock,
            attributes=Attributes(cmd.attributes),
            cover_image_url=cmd.cover_image_url,
            is_active=cmd.is_active,
        )
        return self._repo.save_variant(variant)

    def check_stock(self, variant_id: int, requested_qty: int) -> tuple[bool, str]:
        """Use-case: kiểm tra tồn kho của variant"""
        variant = self._repo.get_variant_by_id(variant_id)
        if variant is None:
            raise VariantNotFound(variant_id)
        return variant.check_availability(requested_qty)

    def get_available_products(self) -> List[Product]:
        """Use-case: lấy danh sách sản phẩm còn hàng"""
        return self._repo.list_products({'is_active': True, 'in_stock_only': True})

    # ── Category use-cases ─────────────────────────────────────────────────

    def list_categories(self) -> List[Category]:
        return self._repo.list_categories()
