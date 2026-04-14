"""
VariantModel — Django ORM model for Variant entity
"""
from django.db import models
from .product_model import ProductModel


class VariantModel(models.Model):
    """Django model ánh xạ Variant domain entity"""
    product = models.ForeignKey(
        ProductModel,
        on_delete=models.CASCADE,
        related_name='variants',
    )
    sku = models.CharField(max_length=100, unique=True)
    price = models.DecimalField(max_digits=12, decimal_places=2)
    stock = models.IntegerField(default=0)
    # e.g. {"edition": "hardcover", "color": "red"}
    attributes = models.JSONField(default=dict, blank=True)
    cover_image_url = models.URLField(max_length=2048, blank=True, null=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        db_table = 'variants'
        ordering = ['sku']

    def __str__(self):
        return f"{self.product.name} — {self.sku}"

    @property
    def in_stock(self) -> bool:
        return self.stock > 0 and self.is_active
