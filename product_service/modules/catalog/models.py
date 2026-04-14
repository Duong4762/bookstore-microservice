"""
Expose catalog ORM models for Django migration autodiscovery.
"""

from modules.catalog.infrastructure.models.brand_model import BrandModel
from modules.catalog.infrastructure.models.category_model import CategoryModel
from modules.catalog.infrastructure.models.product_model import ProductModel
from modules.catalog.infrastructure.models.product_type_model import ProductTypeModel
from modules.catalog.infrastructure.models.variant_model import VariantModel

__all__ = [
    "BrandModel",
    "CategoryModel",
    "ProductModel",
    "ProductTypeModel",
    "VariantModel",
]
