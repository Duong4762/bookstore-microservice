"""
Views for Order API - chỉ xử lý HTTP request/response
"""
from rest_framework import viewsets, status
from rest_framework.response import Response
from .models import Order
from .serializers import OrderSerializer, CreateOrderSerializer
from .services import OrderService


class OrderViewSet(viewsets.ModelViewSet):
    """
    ViewSet cho Order API
    Views chỉ xử lý HTTP layer, business logic nằm trong OrderService
    """
    queryset = Order.objects.all()
    serializer_class = OrderSerializer
    
    def list(self, request, *args, **kwargs):
        """GET /orders/ - Lấy danh sách đơn hàng"""
        customer_id = request.query_params.get('customer_id')
        customer_id = int(customer_id) if customer_id else None
        
        orders = OrderService.get_all_orders(customer_id=customer_id)
        
        page = self.paginate_queryset(orders)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        
        serializer = self.get_serializer(orders, many=True)
        return Response(serializer.data)
    
    def create(self, request, *args, **kwargs):
        """POST /orders/ - Tạo đơn hàng mới từ giỏ hàng"""
        create_serializer = CreateOrderSerializer(data=request.data)
        create_serializer.is_valid(raise_exception=True)
        
        try:
            order = OrderService.create_order(
                customer_id=create_serializer.validated_data['customer_id'],
                cart_id=create_serializer.validated_data['cart_id'],
                shipping_address=create_serializer.validated_data['shipping_address'],
                phone_number=create_serializer.validated_data['phone_number'],
                notes=create_serializer.validated_data.get('notes', '')
            )
            
            serializer = self.get_serializer(order)
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        except ValueError as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )
        except Exception as e:
            return Response(
                {'error': f'Failed to create order: {str(e)}'}, 
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    def retrieve(self, request, *args, **kwargs):
        """GET /orders/{id}/ - Lấy thông tin chi tiết đơn hàng"""
        order = OrderService.get_order_by_id(kwargs.get('pk'))
        if not order:
            return Response(
                {'error': 'Order not found'},
                status=status.HTTP_404_NOT_FOUND
            )
        
        serializer = self.get_serializer(order)
        return Response(serializer.data)
    
    def update(self, request, *args, **kwargs):
        """PUT /orders/{id}/ - Cập nhật đơn hàng"""
        new_status = request.data.get('status')
        if not new_status:
            return Response(
                {'error': 'status is required'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        order = OrderService.update_order_status(kwargs.get('pk'), new_status)
        if not order:
            return Response(
                {'error': 'Order not found'},
                status=status.HTTP_404_NOT_FOUND
            )
        
        serializer = self.get_serializer(order)
        return Response(serializer.data)
    
    def destroy(self, request, *args, **kwargs):
        """DELETE /orders/{id}/ - Xóa đơn hàng"""
        order = OrderService.get_order_by_id(kwargs.get('pk'))
        if not order:
            return Response(
                {'error': 'Order not found'},
                status=status.HTTP_404_NOT_FOUND
            )
        
        order.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)
