"""
Serializers for Product and Variant
"""
from rest_framework import serializers
from modules.catalog.infrastructure.models import ProductModel, VariantModel
from .category_serializer import CategorySimpleSerializer, BrandSerializer


class VariantSerializer(serializers.ModelSerializer):
    in_stock = serializers.ReadOnlyField()

    class Meta:
        model = VariantModel
        fields = [
            'id', 'sku', 'price', 'stock', 'attributes',
            'cover_image_url', 'is_active', 'in_stock'
        ]


class ProductSerializer(serializers.ModelSerializer):
    """Full serializer with nested relations"""
    variants = VariantSerializer(many=True, read_only=True)
    category = CategorySimpleSerializer(read_only=True)
    brand = BrandSerializer(read_only=True)
    category_id = serializers.IntegerField(write_only=True)
    brand_id = serializers.IntegerField(write_only=True)
    product_type_id = serializers.IntegerField(write_only=True)

    # Computed fields from attributes
    author = serializers.SerializerMethodField()
    isbn = serializers.SerializerMethodField()
    language = serializers.SerializerMethodField()
    pages = serializers.SerializerMethodField()

    class Meta:
        model = ProductModel
        fields = [
            'id', 'name', 'slug', 'description',
            'category', 'category_id',
            'brand', 'brand_id',
            'product_type_id',
            'attributes',
            'is_active',
            'created_at', 'updated_at',
            'variants',
            # book-specific derived fields
            'author', 'isbn', 'language', 'pages',
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']

    def get_author(self, obj):
        return (obj.attributes or {}).get('author')

    def get_isbn(self, obj):
        return (obj.attributes or {}).get('isbn')

    def get_language(self, obj):
        return (obj.attributes or {}).get('language', 'Vietnamese')

    def get_pages(self, obj):
        return (obj.attributes or {}).get('pages')

    def create(self, validated_data):
        return ProductModel.objects.create(**validated_data)

    def update(self, instance, validated_data):
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()
        return instance


class ProductListSerializer(serializers.ModelSerializer):
    """Lightweight serializer for list views — no nested variants"""
    category_name = serializers.CharField(source='category.name', read_only=True)
    brand_name = serializers.CharField(source='brand.name', read_only=True)
    min_price = serializers.SerializerMethodField()
    in_stock = serializers.SerializerMethodField()
    author = serializers.SerializerMethodField()

    class Meta:
        model = ProductModel
        fields = [
            'id', 'name', 'slug', 'description',
            'category_name', 'brand_name',
            'is_active', 'min_price', 'in_stock', 'author',
        ]

    def get_min_price(self, obj):
        variants = obj.variants.filter(is_active=True)
        if variants.exists():
            return str(variants.order_by('price').first().price)
        return None

    def get_in_stock(self, obj):
        return obj.variants.filter(is_active=True, stock__gt=0).exists()

    def get_author(self, obj):
        return (obj.attributes or {}).get('author')
