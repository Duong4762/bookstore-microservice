from rest_framework import viewsets, status
from rest_framework.response import Response
from rest_framework.decorators import action
from django.utils import timezone
from .models import Payment
from .serializers import PaymentSerializer, ProcessPaymentSerializer
import requests


class PaymentViewSet(viewsets.ModelViewSet):
    """
    ViewSet cho Payment API
    Cung cấp các endpoint: list, create, retrieve
    """
    queryset = Payment.objects.all()
    serializer_class = PaymentSerializer
    
    def list(self, request, *args, **kwargs):
        """GET /payments/ - Lấy danh sách giao dịch thanh toán"""
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
        """POST /payments/ - Tạo giao dịch thanh toán mới"""
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)
        return Response(serializer.data, status=status.HTTP_201_CREATED)
    
    def retrieve(self, request, *args, **kwargs):
        """GET /payments/{id}/ - Lấy thông tin chi tiết thanh toán"""
        instance = self.get_object()
        serializer = self.get_serializer(instance)
        return Response(serializer.data)
    
    @action(detail=False, methods=['post'])
    def process(self, request):
        """POST /payments/process/ - Xử lý thanh toán (đánh dấu đã thanh toán)"""
        process_serializer = ProcessPaymentSerializer(data=request.data)
        process_serializer.is_valid(raise_exception=True)
        
        payment_id = process_serializer.validated_data['payment_id']
        transaction_id = process_serializer.validated_data.get('transaction_id', '')
        notes = process_serializer.validated_data.get('notes', '')
        
        try:
            payment = Payment.objects.get(id=payment_id)
        except Payment.DoesNotExist:
            return Response(
                {'error': 'Payment not found'}, 
                status=status.HTTP_404_NOT_FOUND
            )
        
        if payment.status == 'completed':
            return Response(
                {'error': 'Payment already completed'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Cập nhật trạng thái thanh toán
        payment.status = 'completed'
        payment.payment_date = timezone.now()
        payment.transaction_id = transaction_id
        payment.notes = notes
        payment.save()
        
        # Cập nhật trạng thái order sang 'paid'
        try:
            order_service_url = f'http://localhost:8004/api/orders/{payment.order_id}/'
            order_data = {'status': 'paid'}
            requests.patch(order_service_url, json=order_data, timeout=5)
        except Exception as e:
            print(f"Failed to update order status: {str(e)}")
        
        serializer = self.get_serializer(payment)
        return Response(serializer.data, status=status.HTTP_200_OK)
    
    @action(detail=True, methods=['post'])
    def refund(self, request, pk=None):
        """POST /payments/{id}/refund/ - Hoàn tiền"""
        payment = self.get_object()
        
        if payment.status != 'completed':
            return Response(
                {'error': 'Only completed payments can be refunded'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        payment.status = 'refunded'
        payment.save()
        
        serializer = self.get_serializer(payment)
        return Response(serializer.data, status=status.HTTP_200_OK)
