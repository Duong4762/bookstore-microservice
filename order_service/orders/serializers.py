from rest_framework import serializers
from .models import Order, OrderItem
import requests


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
        """Lấy tên sách từ Book Service"""
        try:
            book_service_url = f'http://localhost:8002/api/books/{obj.book_id}/'
            response = requests.get(book_service_url, timeout=5)
            if response.status_code == 200:
                return response.json().get('title', 'Unknown')
        except Exception:
            pass
        return 'Unknown'


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
