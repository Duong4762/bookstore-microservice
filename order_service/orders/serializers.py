from rest_framework import serializers
from .models import Order, OrderItem
import requests
import os


class OrderItemSerializer(serializers.ModelSerializer):
    """Serializer cho OrderItem model"""
    
    subtotal = serializers.ReadOnlyField()
    book_title = serializers.SerializerMethodField()
    
    class Meta:
        model = OrderItem
        fields = ['id', 'order', 'book_id', 'quantity', 'price', 
                  'subtotal', 'book_title', 'created_at']
        read_only_fields = ['id', 'created_at']
    
    def get_book_title(self, obj):
        """Lấy tên sản phẩm từ Product Service."""
        try:
            product_service_base = os.environ.get('PRODUCT_SERVICE_URL', 'http://product-service:8000').rstrip('/')
            product_url = f'{product_service_base}/api/products/{obj.book_id}/'
            response = requests.get(product_url, timeout=5)
            if response.status_code == 200:
                payload = response.json()
                # API mới dùng trường name; giữ fallback title cho tương thích.
                return payload.get('name') or payload.get('title') or f'Sản phẩm #{obj.book_id}'
        except Exception:
            pass
        return f'Sản phẩm #{obj.book_id}'


class OrderSerializer(serializers.ModelSerializer):
    """Serializer cho Order model"""
    
    items = OrderItemSerializer(many=True, read_only=True)
    
    class Meta:
        model = Order
        fields = ['id', 'customer_id', 'status', 'total_amount', 
                  'shipping_address', 'phone_number', 'notes', 
                  'items', 'created_at', 'updated_at']
        read_only_fields = ['id', 'created_at', 'updated_at']


class CreateOrderSerializer(serializers.Serializer):
    """Serializer để tạo đơn hàng từ giỏ hàng"""
    
    customer_id = serializers.IntegerField()
    cart_id = serializers.IntegerField()
    shipping_address = serializers.CharField()
    phone_number = serializers.CharField(max_length=20)
    notes = serializers.CharField(required=False, allow_blank=True)
