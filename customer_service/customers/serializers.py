from rest_framework import serializers
from .models import Customer


class CustomerSerializer(serializers.ModelSerializer):
    """Serializer cho Customer model"""
    
    class Meta:
        model = Customer
        fields = ['id', 'email', 'full_name', 'phone_number', 'address', 
                  'date_of_birth', 'created_at', 'updated_at', 'is_active']
        read_only_fields = ['id', 'created_at', 'updated_at']
    
    def create(self, validated_data):
        """
        Tạo customer mới.
        """
        customer = Customer.objects.create(**validated_data)
        return customer
