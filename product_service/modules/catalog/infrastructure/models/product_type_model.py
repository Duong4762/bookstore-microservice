"""
ProductTypeModel — Django ORM model for ProductType entity
"""
from django.db import models


class ProductTypeModel(models.Model):
    name = models.CharField(max_length=255)
    # JSON list of required attribute keys for this product type
    required_attributes = models.JSONField(default=list, blank=True)

    class Meta:
        db_table = 'product_types'
        ordering = ['name']

    def __str__(self):
        return self.name
