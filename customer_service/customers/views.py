"""
Views for Customer API - chỉ xử lý HTTP request/response
"""
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from .models import Customer
from .serializers import CustomerSerializer
from .services import CustomerService


class CustomerViewSet(viewsets.ModelViewSet):
    """
    ViewSet cho Customer API
    Views chỉ xử lý HTTP layer, business logic nằm trong CustomerService
    """
    queryset = Customer.objects.all()
    serializer_class = CustomerSerializer
    
    def list(self, request, *args, **kwargs):
        """GET /customers/ - Lấy danh sách khách hàng"""
        customers = CustomerService.get_all_customers()
        serializer = self.get_serializer(customers, many=True)
        return Response(serializer.data)
    
    def create(self, request, *args, **kwargs):
        """POST /customers/ - Tạo khách hàng mới"""
        try:
            customer = CustomerService.create_customer(request.data)
            serializer = self.get_serializer(customer)
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        except Exception as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )
    
    def retrieve(self, request, *args, **kwargs):
        """GET /customers/{id}/ - Lấy thông tin chi tiết khách hàng"""
        customer = CustomerService.get_customer_by_id(kwargs.get('pk'))
        if not customer:
            return Response(
                {'error': 'Customer not found'},
                status=status.HTTP_404_NOT_FOUND
            )
        
        serializer = self.get_serializer(customer)
        return Response(serializer.data)
    
    def update(self, request, *args, **kwargs):
        """PUT /customers/{id}/ - Cập nhật thông tin khách hàng"""
        partial = kwargs.pop('partial', False)
        customer = CustomerService.update_customer(
            kwargs.get('pk'),
            request.data,
            partial=partial
        )
        
        if not customer:
            return Response(
                {'error': 'Customer not found'},
                status=status.HTTP_404_NOT_FOUND
            )
        
        serializer = self.get_serializer(customer)
        return Response(serializer.data)
    
    def destroy(self, request, *args, **kwargs):
        """DELETE /customers/{id}/ - Xóa khách hàng"""
        success = CustomerService.delete_customer(kwargs.get('pk'))
        if not success:
            return Response(
                {'error': 'Customer not found'},
                status=status.HTTP_404_NOT_FOUND
            )
        
        return Response(status=status.HTTP_204_NO_CONTENT)

    @action(detail=False, methods=['get'], url_path='by-email')
    def by_email(self, request):
        """GET /customers/by-email/?email= - Tra cứu khách theo email (đăng nhập cửa hàng)."""
        email = (request.query_params.get('email') or '').strip()
        if not email:
            return Response({'error': 'email is required'}, status=status.HTTP_400_BAD_REQUEST)
        customer = CustomerService.get_customer_by_email(email)
        if not customer:
            return Response({'error': 'Customer not found'}, status=status.HTTP_404_NOT_FOUND)
        serializer = self.get_serializer(customer)
        return Response(serializer.data)
