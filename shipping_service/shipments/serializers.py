from rest_framework import serializers
from .models import Shipment
import uuid


class ShipmentSerializer(serializers.ModelSerializer):
    """Serializer cho Shipment model"""
    
    class Meta:
        model = Shipment
        fields = ['id', 'order_id', 'tracking_number', 'carrier', 'shipping_address',
                  'status', 'estimated_delivery', 'actual_delivery', 'notes',
                  'created_at', 'updated_at']
        read_only_fields = ['id', 'created_at', 'updated_at', 'tracking_number']
    
    def create(self, validated_data):
        """Tự động tạo tracking number khi tạo shipment"""
        if not validated_data.get('tracking_number'):
            validated_data['tracking_number'] = f"TRK-{uuid.uuid4().hex[:12].upper()}"
        return super().create(validated_data)
