"""
BrandModel — Django ORM model for Brand entity
"""
from django.db import models


class BrandModel(models.Model):
    name = models.CharField(max_length=255)
    slug = models.SlugField(max_length=255, unique=True)
    description = models.TextField(blank=True, default='')
    is_active = models.BooleanField(default=True)

    class Meta:
        db_table = 'brands'
        ordering = ['name']

    def __str__(self):
        return self.name
