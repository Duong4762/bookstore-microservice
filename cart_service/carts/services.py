"""
Service layer for Cart business logic
"""
import os
import requests
from typing import Optional, Dict
from .models import Cart, CartItem
from .serializers import CartSerializer, CartItemSerializer


class CartService:
    """Service class xử lý business logic cho Cart"""
    
    PRODUCT_SERVICE_URL = os.environ.get('PRODUCT_SERVICE_URL', 'http://product-service:8000') + '/api/products'
    
    @staticmethod
    def create_cart(customer_id: int) -> Cart:
        """
        Tạo giỏ hàng mới cho customer
        
        Args:
            customer_id: ID của customer
            
        Returns:
            Cart object đã tạo
        """
        cart = Cart.objects.create(customer_id=customer_id)
        return cart
    
    @staticmethod
    def get_cart_by_customer(customer_id: int) -> Optional[Cart]:
        """
        Lấy giỏ hàng theo customer_id
        
        Args:
            customer_id: ID của customer
            
        Returns:
            Cart object hoặc None nếu không tìm thấy
        """
        try:
            return Cart.objects.get(customer_id=customer_id)
        except Cart.DoesNotExist:
            return None
    
    @staticmethod
    def get_cart_by_id(cart_id: int) -> Optional[Cart]:
        """
        Lấy giỏ hàng theo cart_id
        
        Args:
            cart_id: ID của cart
            
        Returns:
            Cart object hoặc None nếu không tìm thấy
        """
        try:
            return Cart.objects.get(id=cart_id)
        except Cart.DoesNotExist:
            return None
    
    @staticmethod
    def _get_book_info(book_id: int) -> Optional[Dict]:
        """
        Lấy thông tin sách từ Book Service
        
        Args:
            book_id: ID của sách
            
        Returns:
            Dictionary chứa thông tin sách hoặc None
        """
        try:
            response = requests.get(
                f'{CartService.PRODUCT_SERVICE_URL}/{book_id}/',
                timeout=5
            )
            if response.status_code == 200:
                return response.json()
            return None
        except Exception as e:
            print(f"Error fetching book {book_id}: {str(e)}")
            return None


class CartItemService:
    """Service class xử lý business logic cho CartItem"""
    
    @staticmethod
    def add_item_to_cart(cart_id: int, book_id: int, quantity: int = 1) -> CartItem:
        """
        Thêm sách vào giỏ hàng hoặc cập nhật số lượng nếu đã tồn tại
        
        Args:
            cart_id: ID của cart
            book_id: ID của sách
            quantity: Số lượng sách
            
        Returns:
            CartItem object
            
        Raises:
            ValueError: Nếu cart không tồn tại hoặc book không tìm thấy
        """
        # Kiểm tra cart tồn tại
        cart = CartService.get_cart_by_id(cart_id)
        if not cart:
            raise ValueError("Cart not found")
        
        # Lấy thông tin sách từ Book Service
        book_info = CartService._get_book_info(book_id)
        if not book_info:
            raise ValueError("Book not found")
        
        # product_service trả dữ liệu theo nhiều shape; ưu tiên price trực tiếp.
        raw_price = book_info.get('price')
        if raw_price is None:
            raw_price = book_info.get('min_price')
        if raw_price is None and isinstance(book_info.get('variants'), list) and book_info['variants']:
            raw_price = book_info['variants'][0].get('price')
        if raw_price is None:
            raise ValueError("Book price not found")

        price = float(raw_price)
        
        # Kiểm tra xem sách đã có trong giỏ hàng chưa
        cart_item, created = CartItem.objects.get_or_create(
            cart_id=cart_id,
            book_id=book_id,
            defaults={'price': price, 'quantity': quantity}
        )
        
        if not created:
            # Nếu đã tồn tại, cập nhật số lượng
            cart_item.quantity += quantity
            cart_item.save()
        
        return cart_item
    
    @staticmethod
    def update_cart_item_quantity(cart_item_id: int, quantity: int) -> Optional[CartItem]:
        """
        Cập nhật số lượng của cart item
        
        Args:
            cart_item_id: ID của cart item
            quantity: Số lượng mới
            
        Returns:
            CartItem object đã cập nhật hoặc None nếu không tìm thấy
        """
        try:
            cart_item = CartItem.objects.get(id=cart_item_id)
            cart_item.quantity = quantity
            cart_item.save()
            return cart_item
        except CartItem.DoesNotExist:
            return None
    
    @staticmethod
    def remove_item_from_cart(cart_item_id: int) -> bool:
        """
        Xóa sách khỏi giỏ hàng
        
        Args:
            cart_item_id: ID của cart item
            
        Returns:
            True nếu xóa thành công, False nếu không tìm thấy
        """
        try:
            cart_item = CartItem.objects.get(id=cart_item_id)
            cart_item.delete()
            return True
        except CartItem.DoesNotExist:
            return False
    
    @staticmethod
    def clear_cart(cart_id: int) -> None:
        """
        Xóa tất cả items trong giỏ hàng
        
        Args:
            cart_id: ID của cart
        """
        CartItem.objects.filter(cart_id=cart_id).delete()
