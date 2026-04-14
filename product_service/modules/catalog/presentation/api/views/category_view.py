"""
Category and Brand API views
"""
from rest_framework import viewsets

from modules.catalog.infrastructure.models import CategoryModel, BrandModel, ProductTypeModel
from modules.catalog.presentation.api.serializers.category_serializer import (
    CategorySerializer, BrandSerializer, ProductTypeSerializer
)


class CategoryViewSet(viewsets.ModelViewSet):
    """
    CRUD endpoints cho Category.
    GET /api/categories/ — danh sách (cây thư mục root)
    GET /api/categories/{id}/ — chi tiết
    POST /api/categories/ — tạo mới
    PUT/PATCH /api/categories/{id}/ — cập nhật
    DELETE /api/categories/{id}/ — xóa
    """
    serializer_class = CategorySerializer
    queryset = CategoryModel.objects.filter(is_active=True)

    def get_queryset(self):
        """Chỉ trả về root categories (không có parent) trong list view"""
        if self.action == 'list':
            if self.request.query_params.get('flat') == 'true':
                return CategoryModel.objects.filter(is_active=True).order_by('name')
            return CategoryModel.objects.filter(parent__isnull=True, is_active=True)
        return CategoryModel.objects.filter(is_active=True)


class BrandViewSet(viewsets.ModelViewSet):
    serializer_class = BrandSerializer
    queryset = BrandModel.objects.filter(is_active=True)


class ProductTypeViewSet(viewsets.ReadOnlyModelViewSet):
    """GET /api/product-types/ (read-only)."""

    serializer_class = ProductTypeSerializer
    queryset = ProductTypeModel.objects.all().order_by('id')
