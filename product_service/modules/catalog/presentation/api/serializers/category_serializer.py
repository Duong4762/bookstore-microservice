"""
Serializers for Category and Brand
"""
from rest_framework import serializers
from modules.catalog.infrastructure.models import CategoryModel, BrandModel, ProductTypeModel


class CategorySerializer(serializers.ModelSerializer):
    children = serializers.SerializerMethodField()

    class Meta:
        model = CategoryModel
        fields = ['id', 'name', 'slug', 'description', 'parent', 'is_active', 'children']

    def get_children(self, obj):
        children = obj.children.filter(is_active=True)
        return CategorySerializer(children, many=True).data


class CategorySimpleSerializer(serializers.ModelSerializer):
    """Lightweight serializer without children tree (for nested use)"""
    class Meta:
        model = CategoryModel
        fields = ['id', 'name', 'slug']


class BrandSerializer(serializers.ModelSerializer):
    class Meta:
        model = BrandModel
        fields = ['id', 'name', 'slug', 'description', 'is_active']


class ProductTypeSerializer(serializers.ModelSerializer):
    class Meta:
        model = ProductTypeModel
        fields = ['id', 'name', 'required_attributes']
