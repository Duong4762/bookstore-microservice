from rest_framework import serializers
from .models import Customer
import requests


class CustomerSerializer(serializers.ModelSerializer):
    """Serializer cho Customer model"""
    
    class Meta:
        model = Customer
        fields = ['id', 'email', 'full_name', 'phone_number', 'address', 
                  'date_of_birth', 'created_at', 'updated_at', 'is_active']
        read_only_fields = ['id', 'created_at', 'updated_at']
    
    def create(self, validated_data):
        """
        Tạo customer mới và tự động tạo giỏ hàng cho customer
        """
        customer = Customer.objects.create(**validated_data)
        
        # Gọi Cart Service để tạo giỏ hàng cho customer mới
        try:
            cart_service_url = 'http://localhost:8003/api/carts/'
            response = requests.post(
                cart_service_url,
                json={'customer_id': customer.id},
                timeout=5
            )
            if response.status_code == 201:
                print(f"Cart created successfully for customer {customer.id}")
        except Exception as e:
            print(f"Failed to create cart for customer {customer.id}: {str(e)}")
            # Không raise exception để không ảnh hưởng đến việc tạo customer
        
        return customer
