from rest_framework import serializers
from .models import Rating
import requests


class RatingSerializer(serializers.ModelSerializer):
    """Serializer cho Rating model"""
    
    customer_name = serializers.SerializerMethodField()
    book_title = serializers.SerializerMethodField()
    
    class Meta:
        model = Rating
        fields = ['id', 'book_id', 'customer_id', 'rating', 'comment',
                  'customer_name', 'book_title', 'created_at', 'updated_at']
        read_only_fields = ['id', 'created_at', 'updated_at']
    
    def get_customer_name(self, obj):
        """Lấy tên customer từ Customer Service"""
        try:
            customer_service_url = f'http://localhost:8001/api/customers/{obj.customer_id}/'
            response = requests.get(customer_service_url, timeout=5)
            if response.status_code == 200:
                return response.json().get('full_name', 'Unknown')
        except Exception:
            pass
        return 'Unknown'
    
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
    
    def validate_rating(self, value):
        """Validate rating phải từ 1 đến 5"""
        if value < 1 or value > 5:
            raise serializers.ValidationError("Rating phải từ 1 đến 5")
        return value
