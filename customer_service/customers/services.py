"""
Service layer for Customer business logic
"""
import os
import requests
from typing import Optional, List
from .models import Customer
from .serializers import CustomerSerializer


class CustomerService:
    """Service class xử lý business logic cho Customer"""
    
    CART_SERVICE_URL = os.environ.get('CART_SERVICE_URL', 'http://cart-service:8000') + '/api/carts/'
    
    @staticmethod
    def create_customer(data: dict) -> Customer:
        """
        Tạo customer mới và tự động tạo giỏ hàng
        
        Args:
            data: Dictionary chứa thông tin customer
            
        Returns:
            Customer object đã tạo
            
        Raises:
            ValidationError: Nếu data không hợp lệ
        """
        serializer = CustomerSerializer(data=data)
        serializer.is_valid(raise_exception=True)
        customer = serializer.save()
        
        # Tự động tạo giỏ hàng cho customer
        CustomerService._create_cart_for_customer(customer.id)
        
        return customer
    
    @staticmethod
    def _create_cart_for_customer(customer_id: int) -> None:
        """
        Gọi Cart Service để tạo giỏ hàng cho customer
        
        Args:
            customer_id: ID của customer
        """
        try:
            response = requests.post(
                CustomerService.CART_SERVICE_URL,
                json={'customer_id': customer_id},
                timeout=5
            )
            if response.status_code == 201:
                print(f"Cart created successfully for customer {customer_id}")
            else:
                print(f"Failed to create cart for customer {customer_id}: {response.status_code}")
        except Exception as e:
            print(f"Error creating cart for customer {customer_id}: {str(e)}")
            # Không raise exception để không ảnh hưởng đến việc tạo customer
    
    @staticmethod
    def get_all_customers() -> List[Customer]:
        """
        Lấy danh sách tất cả customers
        
        Returns:
            QuerySet của Customer objects
        """
        return Customer.objects.all()
    
    @staticmethod
    def get_customer_by_id(customer_id: int) -> Optional[Customer]:
        """
        Lấy customer theo ID
        
        Args:
            customer_id: ID của customer
            
        Returns:
            Customer object hoặc None nếu không tìm thấy
        """
        try:
            return Customer.objects.get(id=customer_id)
        except Customer.DoesNotExist:
            return None

    @staticmethod
    def get_customer_by_email(email: str) -> Optional[Customer]:
        """Lấy customer theo email (không phân biệt hoa thường)."""
        if not email or not str(email).strip():
            return None
        return Customer.objects.filter(email__iexact=str(email).strip()).first()
    
    @staticmethod
    def update_customer(customer_id: int, data: dict, partial: bool = False) -> Optional[Customer]:
        """
        Cập nhật thông tin customer
        
        Args:
            customer_id: ID của customer
            data: Dictionary chứa dữ liệu cập nhật
            partial: True nếu là partial update (PATCH)
            
        Returns:
            Customer object đã cập nhật hoặc None nếu không tìm thấy
        """
        customer = CustomerService.get_customer_by_id(customer_id)
        if not customer:
            return None
        
        serializer = CustomerSerializer(customer, data=data, partial=partial)
        serializer.is_valid(raise_exception=True)
        return serializer.save()
    
    @staticmethod
    def delete_customer(customer_id: int) -> bool:
        """
        Xóa customer
        
        Args:
            customer_id: ID của customer
            
        Returns:
            True nếu xóa thành công, False nếu không tìm thấy
        """
        customer = CustomerService.get_customer_by_id(customer_id)
        if not customer:
            return False
        
        customer.delete()
        return True
