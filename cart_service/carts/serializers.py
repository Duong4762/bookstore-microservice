from rest_framework import serializers
from .models import Cart, CartItem
import requests


class CartItemSerializer(serializers.ModelSerializer):
    """Serializer cho CartItem model"""
    
    subtotal = serializers.ReadOnlyField()
    book_title = serializers.SerializerMethodField()
    variant_label = serializers.SerializerMethodField()
    
    class Meta:
        model = CartItem
        fields = ['id', 'cart', 'book_id', 'variant_id', 'quantity', 'price',
                  'subtotal', 'book_title', 'variant_label', 'created_at', 'updated_at']
        read_only_fields = ['id', 'created_at', 'updated_at']
    
    def get_book_title(self, obj):
        """Lấy tên sách từ Book Service"""
        try:
            book_service_url = f'http://localhost:8002/api/books/{obj.book_id}/'
            response = requests.get(book_service_url, timeout=5)
            if response.status_code == 200:
                return response.json().get('title', 'Unknown')
        except Exception:
            pass
        return 'Unknown'

    def get_variant_label(self, obj):
        if not obj.variant_id:
            return ''
        return f'Variant #{obj.variant_id}'
    
    def validate_quantity(self, value):
        """Validate số lượng phải lớn hơn 0"""
        if value <= 0:
            raise serializers.ValidationError("Số lượng phải lớn hơn 0")
        return value


class CartSerializer(serializers.ModelSerializer):
    """Serializer cho Cart model"""
    
    items = CartItemSerializer(many=True, read_only=True)
    total_items = serializers.ReadOnlyField()
    total_price = serializers.ReadOnlyField()
    
    class Meta:
        model = Cart
        fields = ['id', 'customer_id', 'items', 'total_items', 'total_price',
                  'created_at', 'updated_at']
        read_only_fields = ['id', 'created_at', 'updated_at']
