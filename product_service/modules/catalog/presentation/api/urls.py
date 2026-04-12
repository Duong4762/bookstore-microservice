"""
API URL routing for product_service
"""
from rest_framework.routers import DefaultRouter
from django.urls import path, include

from modules.catalog.presentation.api.views.product_view import ProductViewSet
from modules.catalog.presentation.api.views.category_view import CategoryViewSet, BrandViewSet

router = DefaultRouter()
router.register(r'products', ProductViewSet, basename='product')
router.register(r'categories', CategoryViewSet, basename='category')
router.register(r'brands', BrandViewSet, basename='brand')

urlpatterns = [
    path('', include(router.urls)),
]
