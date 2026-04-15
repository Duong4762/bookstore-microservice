"""
Serializers for Product and Variant
"""
from rest_framework import serializers
from django.db.models import Sum
from modules.catalog.infrastructure.models import ProductModel, VariantModel
from .category_serializer import CategorySimpleSerializer, BrandSerializer


_ATTRIBUTE_LABELS = {
    'cpu': 'CPU',
    'chipset': 'Chipset',
    'ram': 'RAM',
    'storage': 'Dung lượng lưu trữ',
    'screen_size': 'Kích thước màn hình',
    'resolution': 'Độ phân giải',
    'panel': 'Tấm nền',
    'refresh_rate': 'Tần số quét',
    'sensor': 'Cảm biến',
    'lens': 'Ống kính / ngàm',
    'battery': 'Pin',
    'connectivity': 'Kết nối',
    'speed': 'Tốc độ',
    'ports': 'Cổng kết nối',
    'power': 'Công suất',
    'warranty': 'Bảo hành',
    'compatibility': 'Tương thích',
    'platform': 'Nền tảng',
    'author': 'Tác giả',
    'isbn': 'ISBN',
    'pages': 'Số trang',
    'language': 'Ngôn ngữ',
    'publication_year': 'Năm xuất bản',
}

_PREFERRED_ATTRIBUTE_ORDER = (
    'cpu', 'chipset', 'ram', 'storage', 'screen_size',
    'resolution', 'panel', 'refresh_rate', 'sensor', 'lens',
    'battery', 'connectivity', 'speed', 'ports', 'power',
    'warranty', 'compatibility', 'platform', 'author', 'isbn',
    'pages', 'language', 'publication_year',
)


def _build_rich_description(obj: ProductModel) -> str:
    base = (obj.description or '').strip()
    attrs = obj.attributes or {}
    if not isinstance(attrs, dict):
        attrs = {}

    parts = []
    if base:
        parts.append(base)

    brand_name = getattr(getattr(obj, 'brand', None), 'name', '') or ''
    category_name = getattr(getattr(obj, 'category', None), 'name', '') or ''
    if brand_name or category_name:
        info = 'Danh mục/Hãng: '
        if category_name and brand_name:
            info += f'{category_name} - {brand_name}'
        else:
            info += category_name or brand_name
        parts.append(info)

    ordered_keys = [k for k in _PREFERRED_ATTRIBUTE_ORDER if k in attrs]
    ordered_keys.extend([k for k in attrs.keys() if k not in ordered_keys])
    specs = []
    for key in ordered_keys:
        value = attrs.get(key)
        if value in (None, ''):
            continue
        label = _ATTRIBUTE_LABELS.get(key, key.replace('_', ' ').capitalize())
        specs.append(f'{label}: {value}')
    if specs:
        parts.append(f'Thông số nổi bật: {" | ".join(specs[:10])}')

    variants = obj.variants.filter(is_active=True).order_by('price')
    if variants.exists():
        first_variant = variants.first()
        last_variant = variants.last()
        stock_agg = variants.aggregate(total=Sum('stock'))
        total_stock = int(stock_agg.get('total') or 0)
        variant_count = variants.count()
        if first_variant and last_variant:
            min_price = f'{first_variant.price}'
            max_price = f'{last_variant.price}'
            if min_price == max_price:
                price_text = f'Giá tham khảo: {min_price}'
            else:
                price_text = f'Giá tham khảo: từ {min_price} đến {max_price}'
            stock_text = f'tổng tồn kho: {total_stock}'
            parts.append(f'{price_text}; số biến thể: {variant_count}; {stock_text}')

    if not parts:
        return ''
    return '. '.join(p.rstrip('. ') for p in parts if p).strip() + '.'


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

    def to_representation(self, instance):
        data = super().to_representation(instance)
        data['description'] = _build_rich_description(instance)
        return data


class ProductListSerializer(serializers.ModelSerializer):
    """Lightweight serializer for list views — no nested variants"""
    category_name = serializers.CharField(source='category.name', read_only=True)
    brand_name = serializers.CharField(source='brand.name', read_only=True)
    min_price = serializers.SerializerMethodField()
    in_stock = serializers.SerializerMethodField()
    author = serializers.SerializerMethodField()
    cover_image_url = serializers.SerializerMethodField()

    class Meta:
        model = ProductModel
        fields = [
            'id', 'name', 'slug', 'description',
            'category_name', 'brand_name',
            'is_active', 'min_price', 'in_stock', 'author', 'cover_image_url',
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

    def get_cover_image_url(self, obj):
        variants = obj.variants.filter(is_active=True)
        if variants.exists():
            chosen = variants.order_by('price').first()
            return getattr(chosen, 'cover_image_url', None)
        return None

    def to_representation(self, instance):
        data = super().to_representation(instance)
        data['description'] = _build_rich_description(instance)
        return data
