from rest_framework import viewsets, status
from rest_framework.response import Response
from rest_framework.decorators import action
from django.utils import timezone
from .models import Shipment
from .serializers import ShipmentSerializer
import requests


class ShipmentViewSet(viewsets.ModelViewSet):
    """
    ViewSet cho Shipment API
    Cung cấp các endpoint: list, create, retrieve, update
    """
    queryset = Shipment.objects.all()
    serializer_class = ShipmentSerializer
    
    def list(self, request, *args, **kwargs):
        """GET /shipments/ - Lấy danh sách đơn vận chuyển"""
        order_id = request.query_params.get('order_id')
        queryset = self.filter_queryset(self.get_queryset())
        
        if order_id:
            queryset = queryset.filter(order_id=order_id)
        
        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        
        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)
    
    def create(self, request, *args, **kwargs):
        """POST /shipments/ - Tạo đơn vận chuyển mới"""
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)
        return Response(serializer.data, status=status.HTTP_201_CREATED)
    
    def retrieve(self, request, *args, **kwargs):
        """GET /shipments/{id}/ - Lấy thông tin chi tiết đơn vận chuyển"""
        instance = self.get_object()
        serializer = self.get_serializer(instance)
        return Response(serializer.data)
    
    def update(self, request, *args, **kwargs):
        """PUT /shipments/{id}/ - Cập nhật đơn vận chuyển"""
        partial = kwargs.pop('partial', False)
        instance = self.get_object()
        old_status = instance.status
        
        serializer = self.get_serializer(instance, data=request.data, partial=partial)
        serializer.is_valid(raise_exception=True)
        self.perform_update(serializer)
        
        # Nếu status thay đổi thành 'delivered', cập nhật order status và actual_delivery
        if instance.status == 'delivered' and old_status != 'delivered':
            instance.actual_delivery = timezone.now()
            instance.save()
            
            # Cập nhật order status sang 'delivered'
            try:
                order_service_url = f'http://localhost:8004/api/orders/{instance.order_id}/'
                order_data = {'status': 'delivered'}
                requests.patch(order_service_url, json=order_data, timeout=5)
            except Exception as e:
                print(f"Failed to update order status: {str(e)}")
        
        return Response(serializer.data)
    
    @action(detail=False, methods=['get'])
    def track(self, request):
        """GET /shipments/track/?tracking_number=XXX - Tracking đơn hàng"""
        tracking_number = request.query_params.get('tracking_number')
        if not tracking_number:
            return Response(
                {'error': 'tracking_number is required'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            shipment = Shipment.objects.get(tracking_number=tracking_number)
            serializer = self.get_serializer(shipment)
            return Response(serializer.data)
        except Shipment.DoesNotExist:
            return Response(
                {'error': 'Shipment not found'}, 
                status=status.HTTP_404_NOT_FOUND
            )
    
    @action(detail=True, methods=['post'])
    def start_shipping(self, request, pk=None):
        """POST /shipments/{id}/start_shipping/ - Bắt đầu vận chuyển"""
        shipment = self.get_object()
        
        if shipment.status != 'preparing':
            return Response(
                {'error': 'Shipment is not in preparing status'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        shipment.status = 'shipping'
        shipment.save()
        
        # Cập nhật order status
        try:
            order_service_url = f'http://localhost:8004/api/orders/{shipment.order_id}/'
            order_data = {'status': 'shipped'}
            requests.patch(order_service_url, json=order_data, timeout=5)
        except Exception as e:
            print(f"Failed to update order status: {str(e)}")
        
        serializer = self.get_serializer(shipment)
        return Response(serializer.data, status=status.HTTP_200_OK)
