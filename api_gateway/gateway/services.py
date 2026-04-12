"""
Service layer for API Gateway - xử lý business logic và giao tiếp với microservices
"""
import requests
from typing import Optional, Dict, List


CUSTOMER_SERVICE_URL = 'http://localhost:8001/api'
PRODUCT_SERVICE_URL = 'http://localhost:8002/api'
CART_SERVICE_URL = 'http://localhost:8003/api'
ORDER_SERVICE_URL = 'http://localhost:8004/api'
PAYMENT_SERVICE_URL = 'http://localhost:8005/api'
SHIPPING_SERVICE_URL = 'http://localhost:8006/api'
RATING_SERVICE_URL = 'http://localhost:8007/api'


class CustomerGatewayService:
    """Service xử lý logic liên quan đến Customer"""
    
    @staticmethod
    def get_all_customers() -> List[Dict]:
        """Lấy danh sách customers"""
        try:
            response = requests.get(f'{CUSTOMER_SERVICE_URL}/customers/', timeout=5)
            if response.status_code == 200:
                data = response.json()
                return data.get('results', data) if isinstance(data, dict) else data
            return []
        except Exception as e:
            print(f"Error fetching customers: {str(e)}")
            return []
    
    @staticmethod
    def create_customer(data: Dict) -> tuple[bool, Optional[Dict], str]:
        """
        Tạo customer mới
        
        Returns:
            Tuple (success: bool, customer_data: Dict, message: str)
        """
        try:
            response = requests.post(f'{CUSTOMER_SERVICE_URL}/customers/', json=data, timeout=5)
            if response.status_code == 201:
                return True, response.json(), 'Đăng ký khách hàng thành công!'
            else:
                return False, None, 'Đăng ký thất bại. Vui lòng kiểm tra lại thông tin.'
        except Exception as e:
            return False, None, f'Lỗi: {str(e)}'


class ProductGatewayService:
    """Service xử lý logic liên quan đến Product (product_service - DDD)"""
    
    @staticmethod
    def get_all_products() -> List[Dict]:
        """Lấy danh sách sản phẩm"""
        try:
            response = requests.get(f'{PRODUCT_SERVICE_URL}/products/', timeout=5)
            if response.status_code == 200:
                data = response.json()
                return data.get('results', data) if isinstance(data, dict) else data
            return []
        except Exception as e:
            print(f"Error fetching products: {str(e)}")
            return []
    
    @staticmethod
    def get_product_by_id(product_id: int) -> Optional[Dict]:
        """Lấy thông tin chi tiết sản phẩm"""
        try:
            response = requests.get(f'{PRODUCT_SERVICE_URL}/products/{product_id}/', timeout=5)
            if response.status_code == 200:
                return response.json()
            return None
        except Exception as e:
            print(f"Error fetching product {product_id}: {str(e)}")
            return None

    @staticmethod
    def get_available_products() -> List[Dict]:
        """Lấy sản phẩm còn hàng"""
        try:
            response = requests.get(f'{PRODUCT_SERVICE_URL}/products/available/', timeout=5)
            if response.status_code == 200:
                data = response.json()
                return data.get('results', data) if isinstance(data, dict) else data
            return []
        except Exception as e:
            print(f"Error fetching available products: {str(e)}")
            return []


class CartGatewayService:
    """Service xử lý logic liên quan đến Cart"""
    
    @staticmethod
    def get_cart_by_customer(customer_id: int) -> Optional[Dict]:
        """Lấy giỏ hàng theo customer_id"""
        try:
            response = requests.get(
                f'{CART_SERVICE_URL}/carts/by_customer/',
                params={'customer_id': customer_id},
                timeout=5
            )
            if response.status_code == 200:
                return response.json()
            return None
        except Exception as e:
            print(f"Error fetching cart for customer {customer_id}: {str(e)}")
            return None
    
    @staticmethod
    def add_item_to_cart(customer_id: int, book_id: int, quantity: int = 1) -> tuple[bool, str]:
        """
        Thêm sách vào giỏ hàng
        
        Returns:
            Tuple (success: bool, message: str)
        """
        try:
            # Lấy cart_id từ customer_id
            cart_response = requests.get(
                f'{CART_SERVICE_URL}/carts/by_customer/',
                params={'customer_id': customer_id},
                timeout=5
            )
            
            if cart_response.status_code != 200:
                return False, 'Không tìm thấy giỏ hàng'
            
            cart = cart_response.json()
            cart_id = cart['id']
            
            # Thêm sách vào giỏ hàng
            data = {
                'cart_id': cart_id,
                'book_id': book_id,
                'quantity': quantity
            }
            
            response = requests.post(f'{CART_SERVICE_URL}/cart-items/', json=data, timeout=5)
            if response.status_code in [200, 201]:
                return True, 'Đã thêm sách vào giỏ hàng!'
            else:
                return False, 'Không thể thêm sách vào giỏ hàng'
                
        except Exception as e:
            return False, f'Lỗi: {str(e)}'


class OrderGatewayService:
    """Service xử lý logic liên quan đến Order"""
    
    @staticmethod
    def get_all_orders(customer_id: Optional[int] = None) -> List[Dict]:
        """Lấy danh sách đơn hàng"""
        try:
            params = {'customer_id': customer_id} if customer_id else {}
            response = requests.get(f'{ORDER_SERVICE_URL}/orders/', params=params, timeout=5)
            if response.status_code == 200:
                data = response.json()
                return data.get('results', data) if isinstance(data, dict) else data
            return []
        except Exception as e:
            print(f"Error fetching orders: {str(e)}")
            return []
    
    @staticmethod
    def get_order_by_id(order_id: int) -> Optional[Dict]:
        """Lấy thông tin chi tiết đơn hàng"""
        try:
            response = requests.get(f'{ORDER_SERVICE_URL}/orders/{order_id}/', timeout=5)
            if response.status_code == 200:
                return response.json()
            return None
        except Exception as e:
            print(f"Error fetching order {order_id}: {str(e)}")
            return None
    
    @staticmethod
    def create_order(data: Dict) -> tuple[bool, Optional[Dict], str]:
        """
        Tạo đơn hàng
        
        Returns:
            Tuple (success: bool, order_data: Dict, message: str)
        """
        try:
            response = requests.post(f'{ORDER_SERVICE_URL}/orders/', json=data, timeout=10)
            if response.status_code == 201:
                order = response.json()
                return True, order, f'Đặt hàng thành công! Mã đơn hàng: #{order["id"]}'
            else:
                return False, None, 'Đặt hàng thất bại'
        except Exception as e:
            return False, None, f'Lỗi: {str(e)}'


class PaymentGatewayService:
    """Service xử lý logic liên quan đến Payment"""
    
    @staticmethod
    def get_payment_by_order(order_id: int) -> Optional[Dict]:
        """Lấy thông tin payment theo order_id"""
        try:
            response = requests.get(
                f'{PAYMENT_SERVICE_URL}/payments/',
                params={'order_id': order_id},
                timeout=5
            )
            if response.status_code == 200:
                payments = response.json().get('results', [])
                return payments[0] if payments else None
            return None
        except Exception as e:
            print(f"Error fetching payment for order {order_id}: {str(e)}")
            return None


class ShippingGatewayService:
    """Service xử lý logic liên quan đến Shipping"""
    
    @staticmethod
    def get_shipment_by_order(order_id: int) -> Optional[Dict]:
        """Lấy thông tin shipment theo order_id"""
        try:
            response = requests.get(
                f'{SHIPPING_SERVICE_URL}/shipments/',
                params={'order_id': order_id},
                timeout=5
            )
            if response.status_code == 200:
                shipments = response.json().get('results', [])
                return shipments[0] if shipments else None
            return None
        except Exception as e:
            print(f"Error fetching shipment for order {order_id}: {str(e)}")
            return None


class RatingGatewayService:
    """Service xử lý logic liên quan đến Rating"""
    
    @staticmethod
    def get_ratings_by_book(book_id: int) -> List[Dict]:
        """Lấy danh sách ratings theo book_id"""
        try:
            response = requests.get(
                f'{RATING_SERVICE_URL}/ratings/',
                params={'book_id': book_id},
                timeout=5
            )
            if response.status_code == 200:
                data = response.json()
                return data.get('results', [])
            return []
        except Exception as e:
            print(f"Error fetching ratings for book {book_id}: {str(e)}")
            return []
    
    @staticmethod
    def get_book_stats(book_id: int) -> Dict:
        """Lấy thống kê ratings cho sách"""
        try:
            response = requests.get(
                f'{RATING_SERVICE_URL}/ratings/book_stats/',
                params={'book_id': book_id},
                timeout=5
            )
            if response.status_code == 200:
                return response.json()
            return {}
        except Exception as e:
            print(f"Error fetching stats for book {book_id}: {str(e)}")
            return {}
    
    @staticmethod
    def add_rating(data: Dict) -> tuple[bool, str]:
        """
        Thêm đánh giá sách
        
        Returns:
            Tuple (success: bool, message: str)
        """
        try:
            response = requests.post(f'{RATING_SERVICE_URL}/ratings/', json=data, timeout=5)
            if response.status_code == 201:
                return True, 'Đã thêm đánh giá!'
            else:
                error_data = response.json()
                return False, error_data.get('error', 'Không thể thêm đánh giá')
        except Exception as e:
            return False, f'Lỗi: {str(e)}'
