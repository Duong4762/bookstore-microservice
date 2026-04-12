"""
Category and Brand API views
"""
from rest_framework import viewsets, status
from rest_framework.response import Response

from modules.catalog.infrastructure.models import CategoryModel, BrandModel
from modules.catalog.presentation.api.serializers.category_serializer import (
    CategorySerializer, BrandSerializer
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
            return CategoryModel.objects.filter(parent__isnull=True, is_active=True)
        return CategoryModel.objects.filter(is_active=True)


class BrandViewSet(viewsets.ModelViewSet):
    serializer_class = BrandSerializer
    queryset = BrandModel.objects.filter(is_active=True)
