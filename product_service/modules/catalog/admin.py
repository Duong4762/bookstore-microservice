"""
Admin registration for catalog models
"""
from django.contrib import admin
from modules.catalog.infrastructure.models import (
    ProductModel, VariantModel, CategoryModel, BrandModel, ProductTypeModel
)


@admin.register(CategoryModel)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ['name', 'slug', 'parent', 'is_active']
    list_filter = ['is_active', 'parent']
    search_fields = ['name', 'slug']
    prepopulated_fields = {'slug': ('name',)}


@admin.register(BrandModel)
class BrandAdmin(admin.ModelAdmin):
    list_display = ['name', 'slug', 'is_active']
    search_fields = ['name']
    prepopulated_fields = {'slug': ('name',)}


@admin.register(ProductTypeModel)
class ProductTypeAdmin(admin.ModelAdmin):
    list_display = ['name']
    search_fields = ['name']


@admin.register(ProductModel)
class ProductAdmin(admin.ModelAdmin):
    list_display = ['name', 'slug', 'category', 'brand', 'is_active', 'created_at']
    list_filter = ['is_active', 'category', 'brand', 'product_type']
    search_fields = ['name', 'slug', 'attributes']
    readonly_fields = ['created_at', 'updated_at']
    prepopulated_fields = {'slug': ('name',)}


@admin.register(VariantModel)
class VariantAdmin(admin.ModelAdmin):
    list_display = ['sku', 'product', 'price', 'stock', 'is_active', 'in_stock']
    list_filter = ['is_active', 'product__category']
    search_fields = ['sku', 'product__name']
