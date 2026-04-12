from rest_framework import serializers
from .models import Payment
import requests


class PaymentSerializer(serializers.ModelSerializer):
    """Serializer cho Payment model"""
    
    class Meta:
        model = Payment
        fields = ['id', 'order_id', 'amount', 'payment_method', 'status',
                  'transaction_id', 'payment_date', 'notes', 'created_at', 'updated_at']
        read_only_fields = ['id', 'created_at', 'updated_at']
    
    def validate_amount(self, value):
        """Validate số tiền phải lớn hơn 0"""
        if value <= 0:
            raise serializers.ValidationError("Số tiền phải lớn hơn 0")
        return value


class ProcessPaymentSerializer(serializers.Serializer):
    """Serializer để xử lý thanh toán"""
    
    payment_id = serializers.IntegerField()
    transaction_id = serializers.CharField(max_length=100, required=False)
    notes = serializers.CharField(required=False, allow_blank=True)
