"""
ProductModel — Django ORM model for Product aggregate root
"""
from django.db import models
from .category_model import CategoryModel
from .brand_model import BrandModel
from .product_type_model import ProductTypeModel
from modules.catalog.infrastructure.querysets.product_queryset import ProductQuerySet


class ProductModel(models.Model):
    """Django model ánh xạ Product domain entity"""
    name = models.CharField(max_length=500)
    slug = models.SlugField(max_length=500, unique=True)
    description = models.TextField(blank=True, default='')
    category = models.ForeignKey(
        CategoryModel,
        on_delete=models.PROTECT,
        related_name='products',
    )
    brand = models.ForeignKey(
        BrandModel,
        on_delete=models.PROTECT,
        related_name='products',
    )
    product_type = models.ForeignKey(
        ProductTypeModel,
        on_delete=models.PROTECT,
        related_name='products',
    )
    # Flexible attributes stored as JSON (author, isbn, pages, language, etc.)
    attributes = models.JSONField(default=dict, blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    objects = ProductQuerySet.as_manager()

    class Meta:
        db_table = 'products'
        ordering = ['-created_at']

    def __str__(self):
        return self.name
