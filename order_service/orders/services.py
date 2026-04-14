"""
Service layer for Order business logic
"""
import os
import requests
from typing import Optional, Dict, List
from django.db import transaction
from .models import Order, OrderItem
from .serializers import OrderSerializer


class OrderService:
    """Service class xử lý business logic cho Order"""
    
    CART_SERVICE_URL = os.environ.get('CART_SERVICE_URL', 'http://cart-service:8000') + '/api'
    PAYMENT_SERVICE_URL = os.environ.get('PAYMENT_SERVICE_URL', 'http://payment-service:8000') + '/api/payments/'
    SHIPPING_SERVICE_URL = os.environ.get('SHIPPING_SERVICE_URL', 'http://shipping-service:8000') + '/api/shipments/'
    
    @staticmethod
    def _get_cart_data(cart_id: int) -> Optional[Dict]:
        """
        Lấy thông tin giỏ hàng từ Cart Service
        
        Args:
            cart_id: ID của cart
            
        Returns:
            Dictionary chứa thông tin cart hoặc None
        """
        try:
            response = requests.get(
                f'{OrderService.CART_SERVICE_URL}/carts/{cart_id}/',
                timeout=5
            )
            if response.status_code == 200:
                return response.json()
            return None
        except Exception as e:
            print(f"Error fetching cart {cart_id}: {str(e)}")
            return None
    
    @staticmethod
    def _clear_cart(cart_items: List[Dict]) -> None:
        """
        Xóa các items trong giỏ hàng sau khi tạo đơn
        
        Args:
            cart_items: Danh sách các cart items
        """
        for item in cart_items:
            try:
                requests.delete(
                    f"{OrderService.CART_SERVICE_URL}/cart-items/{item['id']}/",
                    timeout=5
                )
            except Exception as e:
                print(f"Error deleting cart item {item['id']}: {str(e)}")
    
    @staticmethod
    def _create_payment(order_id: int, amount: float) -> None:
        """
        Tạo payment cho đơn hàng
        
        Args:
            order_id: ID của order
            amount: Số tiền
        """
        try:
            payment_data = {
                'order_id': order_id,
                'amount': amount,
                'payment_method': 'COD'
            }
            requests.post(
                OrderService.PAYMENT_SERVICE_URL,
                json=payment_data,
                timeout=5
            )
        except Exception as e:
            print(f"Error creating payment for order {order_id}: {str(e)}")
    
    @staticmethod
    @transaction.atomic
    def create_order(customer_id: int, cart_id: int, shipping_address: str,
                    phone_number: str, notes: str = "") -> Order:
        """
        Tạo đơn hàng mới từ giỏ hàng
        
        Args:
            customer_id: ID của customer
            cart_id: ID của cart
            shipping_address: Địa chỉ giao hàng
            phone_number: Số điện thoại
            notes: Ghi chú
            
        Returns:
            Order object đã tạo
            
        Raises:
            ValueError: Nếu cart không hợp lệ
        """
        # Lấy thông tin giỏ hàng
        cart_data = OrderService._get_cart_data(cart_id)
        if not cart_data:
            raise ValueError("Cart not found")
        
        if not cart_data.get('items'):
            raise ValueError("Cart is empty")
        
        # Tạo đơn hàng
        order = Order.objects.create(
            customer_id=customer_id,
            total_amount=cart_data['total_price'],
            shipping_address=shipping_address,
            phone_number=phone_number,
            notes=notes
        )
        
        # Tạo các order items
        for cart_item in cart_data['items']:
            OrderItem.objects.create(
                order=order,
                book_id=cart_item['book_id'],
                quantity=cart_item['quantity'],
                price=cart_item['price']
            )
        
        # Tạo payment
        OrderService._create_payment(order.id, float(order.total_amount))
        
        # Xóa giỏ hàng
        OrderService._clear_cart(cart_data['items'])
        
        return order
    
    @staticmethod
    def get_all_orders(customer_id: Optional[int] = None) -> List[Order]:
        """
        Lấy danh sách đơn hàng
        
        Args:
            customer_id: Lọc theo customer_id (optional)
            
        Returns:
            QuerySet của Order objects
        """
        if customer_id:
            return Order.objects.filter(customer_id=customer_id)
        return Order.objects.all()
    
    @staticmethod
    def get_order_by_id(order_id: int) -> Optional[Order]:
        """
        Lấy đơn hàng theo ID
        
        Args:
            order_id: ID của order
            
        Returns:
            Order object hoặc None
        """
        try:
            return Order.objects.get(id=order_id)
        except Order.DoesNotExist:
            return None
    
    @staticmethod
    def update_order_status(order_id: int, new_status: str) -> Optional[Order]:
        """
        Cập nhật trạng thái đơn hàng
        
        Args:
            order_id: ID của order
            new_status: Trạng thái mới
            
        Returns:
            Order object đã cập nhật hoặc None
        """
        order = OrderService.get_order_by_id(order_id)
        if not order:
            return None
        
        old_status = order.status
        order.status = new_status
        order.save()
        
        # Nếu status thay đổi sang 'paid', tạo shipment
        if new_status == 'paid' and old_status != 'paid':
            OrderService._create_shipment(order)
        
        return order
    
    @staticmethod
    def _create_shipment(order: Order) -> None:
        """
        Tạo shipment cho đơn hàng đã thanh toán
        
        Args:
            order: Order object
        """
        try:
            shipping_data = {
                'order_id': order.id,
                'shipping_address': order.shipping_address
            }
            requests.post(
                OrderService.SHIPPING_SERVICE_URL,
                json=shipping_data,
                timeout=5
            )
        except Exception as e:
            print(f"Error creating shipment for order {order.id}: {str(e)}")
