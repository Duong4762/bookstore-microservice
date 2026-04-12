"""
ProductRepositoryImpl — Django ORM implementation of AbstractProductRepository.
This is the "Adapter" in the ports & adapters (hexagonal) architecture.
Translates between Django ORM models ↔ Domain entities.
"""
from __future__ import annotations
from typing import Optional, List
from decimal import Decimal

from modules.catalog.domain.entities import Product, Variant, Category
from modules.catalog.domain.value_objects import Money, SKU, Attributes
from modules.catalog.domain.repositories.product_repository import AbstractProductRepository
from modules.catalog.infrastructure.models import (
    ProductModel, VariantModel, CategoryModel
)
from modules.catalog.infrastructure.querysets.product_queryset import ProductQuerySet


class ProductRepositoryImpl(AbstractProductRepository):
    """Concrete implementation using Django ORM"""

    # ── Mapping helpers ────────────────────────────────────────────────────

    @staticmethod
    def _model_to_product(model: ProductModel) -> Product:
        return Product(
            id=model.id,
            name=model.name,
            slug=model.slug,
            description=model.description,
            category_id=model.category_id,
            brand_id=model.brand_id,
            product_type_id=model.product_type_id,
            attributes=Attributes(model.attributes or {}),
            is_active=model.is_active,
            created_at=model.created_at,
            updated_at=model.updated_at,
        )

    @staticmethod
    def _model_to_variant(model: VariantModel) -> Variant:
        return Variant(
            id=model.id,
            product_id=model.product_id,
            sku=SKU(model.sku),
            price=Money.of(model.price),
            stock=model.stock,
            attributes=Attributes(model.attributes or {}),
            cover_image_url=model.cover_image_url,
            is_active=model.is_active,
        )

    @staticmethod
    def _model_to_category(model: CategoryModel) -> Category:
        return Category(
            id=model.id,
            name=model.name,
            slug=model.slug,
            description=model.description,
            parent_id=model.parent_id,
            is_active=model.is_active,
        )

    # ── Product operations ─────────────────────────────────────────────────

    def get_product_by_id(self, product_id: int) -> Optional[Product]:
        try:
            model = ProductModel.objects.with_prefetch().get(id=product_id)
            return self._model_to_product(model)
        except ProductModel.DoesNotExist:
            return None

    def get_product_by_slug(self, slug: str) -> Optional[Product]:
        try:
            model = ProductModel.objects.with_prefetch().get(slug=slug)
            return self._model_to_product(model)
        except ProductModel.DoesNotExist:
            return None

    def list_products(self, filters: dict = None) -> List[Product]:
        qs: ProductQuerySet = ProductModel.objects.with_prefetch()

        if filters:
            if filters.get('is_active'):
                qs = qs.active()
            if filters.get('in_stock_only'):
                qs = qs.in_stock()
            if filters.get('category_id'):
                qs = qs.by_category(filters['category_id'])
            if filters.get('brand_id'):
                qs = qs.by_brand(filters['brand_id'])
            if filters.get('search'):
                qs = qs.search(filters['search'])
            min_price = filters.get('min_price')
            max_price = filters.get('max_price')
            if min_price or max_price:
                qs = qs.price_range(min_price, max_price)
            ordering = filters.get('ordering', '-created_at')
            qs = qs.order_by(ordering)

        return [self._model_to_product(m) for m in qs]

    def save_product(self, product: Product) -> Product:
        defaults = {
            'name': product.name,
            'slug': product.slug,
            'description': product.description,
            'category_id': product.category_id,
            'brand_id': product.brand_id,
            'product_type_id': product.product_type_id,
            'attributes': product.attributes.data,
            'is_active': product.is_active,
        }
        if product.id:
            ProductModel.objects.filter(id=product.id).update(**defaults)
            model = ProductModel.objects.with_prefetch().get(id=product.id)
        else:
            model = ProductModel.objects.create(**defaults)
        return self._model_to_product(model)

    def delete_product(self, product_id: int) -> bool:
        deleted, _ = ProductModel.objects.filter(id=product_id).delete()
        return deleted > 0

    # ── Variant operations ─────────────────────────────────────────────────

    def get_variant_by_id(self, variant_id: int) -> Optional[Variant]:
        try:
            model = VariantModel.objects.get(id=variant_id)
            return self._model_to_variant(model)
        except VariantModel.DoesNotExist:
            return None

    def get_variants_by_product(self, product_id: int) -> List[Variant]:
        models = VariantModel.objects.filter(product_id=product_id)
        return [self._model_to_variant(m) for m in models]

    def save_variant(self, variant: Variant) -> Variant:
        defaults = {
            'product_id': variant.product_id,
            'sku': variant.sku.value,
            'price': variant.price.amount,
            'stock': variant.stock,
            'attributes': variant.attributes.data,
            'cover_image_url': variant.cover_image_url,
            'is_active': variant.is_active,
        }
        if variant.id:
            VariantModel.objects.filter(id=variant.id).update(**defaults)
            model = VariantModel.objects.get(id=variant.id)
        else:
            model = VariantModel.objects.create(**defaults)
        return self._model_to_variant(model)

    def delete_variant(self, variant_id: int) -> bool:
        deleted, _ = VariantModel.objects.filter(id=variant_id).delete()
        return deleted > 0

    # ── Category operations ────────────────────────────────────────────────

    def get_category_by_id(self, category_id: int) -> Optional[Category]:
        try:
            model = CategoryModel.objects.get(id=category_id)
            return self._model_to_category(model)
        except CategoryModel.DoesNotExist:
            return None

    def list_categories(self) -> List[Category]:
        models = CategoryModel.objects.filter(is_active=True).order_by('name')
        return [self._model_to_category(m) for m in models]

    def save_category(self, category: Category) -> Category:
        defaults = {
            'name': category.name,
            'slug': category.slug,
            'description': category.description,
            'parent_id': category.parent_id,
            'is_active': category.is_active,
        }
        if category.id:
            CategoryModel.objects.filter(id=category.id).update(**defaults)
            model = CategoryModel.objects.get(id=category.id)
        else:
            model = CategoryModel.objects.create(**defaults)
        return self._model_to_category(model)
