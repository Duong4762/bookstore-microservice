"""
Service layer for API Gateway - xử lý business logic và giao tiếp với microservices
"""
import os
import requests
from typing import Any, Dict, List, Optional


CUSTOMER_SERVICE_URL = f"{os.environ.get('CUSTOMER_SERVICE_URL', 'http://localhost:8001')}/api"
PRODUCT_SERVICE_URL = f"{os.environ.get('PRODUCT_SERVICE_URL', 'http://localhost:8002')}/api"
CART_SERVICE_URL = f"{os.environ.get('CART_SERVICE_URL', 'http://localhost:8003')}/api"
ORDER_SERVICE_URL = f"{os.environ.get('ORDER_SERVICE_URL', 'http://localhost:8004')}/api"
PAYMENT_SERVICE_URL = f"{os.environ.get('PAYMENT_SERVICE_URL', 'http://localhost:8005')}/api"
SHIPPING_SERVICE_URL = f"{os.environ.get('SHIPPING_SERVICE_URL', 'http://localhost:8006')}/api"
RATING_SERVICE_URL = f"{os.environ.get('RATING_SERVICE_URL', 'http://localhost:8007')}/api"
RECOMMENDER_SERVICE_URL = os.environ.get('RECOMMENDER_SERVICE_URL', 'http://localhost:8008')


def _drf_paginated_results(url: str, params: Optional[Dict] = None) -> List[Dict]:
    """Gom cac trang khi API DRF tra ve results/next."""
    rows: List[Dict] = []
    page = 1
    base = dict(params or {})
    while page < 100:
        query = {**base, 'page': page}
        response = requests.get(url, params=query, timeout=15)
        if response.status_code != 200:
            break
        data = response.json()
        if isinstance(data, list):
            return data
        batch = data.get('results')
        if batch is None:
            break
        rows.extend(batch)
        if not data.get('next'):
            break
        page += 1
    return rows


STAFF_USERNAME = os.environ.get('STAFF_USERNAME', 'staff')
STAFF_PASSWORD = os.environ.get('STAFF_PASSWORD', 'staff123')
SESSION_STAFF_KEY = 'staff_authenticated'


class StaffAuthService:
    """Dang nhap nhan vien qua bien moi truong (khong co dang ky)."""

    @staticmethod
    def verify(username: str, password: str) -> bool:
        u = (username or '').strip()
        p = password or ''
        return u == STAFF_USERNAME and p == STAFF_PASSWORD


class CustomerGatewayService:
    """Service xử lý logic liên quan đến Customer"""

    @staticmethod
    def get_customer_by_id(customer_id: int) -> Optional[Dict]:
        try:
            response = requests.get(f'{CUSTOMER_SERVICE_URL}/customers/{customer_id}/', timeout=5)
            if response.status_code == 200:
                return response.json()
            return None
        except Exception as e:
            print(f"Error fetching customer {customer_id}: {str(e)}")
            return None

    @staticmethod
    def get_all_customers() -> List[Dict]:
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
    def get_customer_by_email(email: str) -> Optional[Dict]:
        email = (email or '').strip()
        if not email:
            return None
        try:
            response = requests.get(
                f'{CUSTOMER_SERVICE_URL}/customers/by-email/',
                params={'email': email},
                timeout=5,
            )
            if response.status_code == 200:
                return response.json()
            return None
        except Exception as e:
            print(f"Error fetching customer by email: {str(e)}")
            return None

    @staticmethod
    def create_customer(data: Dict) -> tuple[bool, Optional[Dict], str]:
        try:
            response = requests.post(f'{CUSTOMER_SERVICE_URL}/customers/', json=data, timeout=5)
            if response.status_code == 201:
                return True, response.json(), 'Đăng ký khách hàng thành công!'
            detail = 'Đăng ký thất bại. Vui lòng kiểm tra lại thông tin.'
            try:
                payload = response.json()
                if isinstance(payload, dict) and payload:
                    first_key, first_val = next(iter(payload.items()))
                    if isinstance(first_val, list) and first_val:
                        detail = f'{first_key}: {first_val[0]}'
                    elif isinstance(first_val, str):
                        detail = f'{first_key}: {first_val}'
            except Exception:
                pass
            return False, None, detail
        except Exception as e:
            return False, None, f'Loi: {str(e)}'


class ProductGatewayService:
    """Service xử lý logic liên quan đến Product (product_service - DDD)"""

    @staticmethod
    def get_all_products() -> List[Dict]:
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
        try:
            response = requests.get(f'{PRODUCT_SERVICE_URL}/products/available/', timeout=5)
            if response.status_code == 200:
                data = response.json()
                return data.get('results', data) if isinstance(data, dict) else data
            return []
        except Exception as e:
            print(f"Error fetching available products: {str(e)}")
            return []

    @staticmethod
    def list_products_for_staff(*, search: Optional[str] = None) -> List[Dict]:
        try:
            params: Dict[str, str] = {'include_inactive': 'true'}
            if search:
                params['search'] = search
            response = requests.get(f'{PRODUCT_SERVICE_URL}/products/', params=params, timeout=10)
            if response.status_code == 200:
                data = response.json()
                return data.get('results', data) if isinstance(data, dict) else data
            return []
        except Exception as e:
            print(f"Error fetching staff products: {str(e)}")
            return []

    @staticmethod
    def _format_product_api_error(response: requests.Response) -> str:
        try:
            payload = response.json()
            if isinstance(payload, dict) and payload.get('error'):
                return str(payload['error'])
            if isinstance(payload, dict) and payload:
                key, val = next(iter(payload.items()))
                if isinstance(val, list) and val:
                    return f'{key}: {val[0]}'
                return str(val)
        except Exception:
            pass
        return f'Thất bại (HTTP {response.status_code})'

    @staticmethod
    def create_product(payload: Dict) -> tuple[bool, Optional[Dict], str]:
        try:
            response = requests.post(f'{PRODUCT_SERVICE_URL}/products/', json=payload, timeout=10)
            if response.status_code == 201:
                return True, response.json(), 'Da tao san pham.'
            return False, None, ProductGatewayService._format_product_api_error(response)
        except Exception as e:
            return False, None, f'Loi: {str(e)}'

    @staticmethod
    def update_product(product_id: int, payload: Dict) -> tuple[bool, Optional[Dict], str]:
        try:
            response = requests.put(
                f'{PRODUCT_SERVICE_URL}/products/{product_id}/',
                json=payload,
                timeout=10,
            )
            if response.status_code == 200:
                return True, response.json(), 'Da cap nhat san pham.'
            return False, None, ProductGatewayService._format_product_api_error(response)
        except Exception as e:
            return False, None, f'Loi: {str(e)}'

    @staticmethod
    def delete_product(product_id: int) -> tuple[bool, str]:
        try:
            response = requests.delete(f'{PRODUCT_SERVICE_URL}/products/{product_id}/', timeout=10)
            if response.status_code in (200, 204):
                return True, 'Da xoa san pham.'
            return False, ProductGatewayService._format_product_api_error(response)
        except Exception as e:
            return False, f'Loi: {str(e)}'

    @staticmethod
    def create_variant(product_id: int, payload: Dict) -> tuple[bool, Optional[Dict], str]:
        try:
            response = requests.post(
                f'{PRODUCT_SERVICE_URL}/products/{product_id}/variants/',
                json=payload,
                timeout=10,
            )
            if response.status_code == 201:
                return True, response.json(), 'Đã thêm biến thể.'
            return False, None, ProductGatewayService._format_product_api_error(response)
        except Exception as e:
            return False, None, f'Loi: {str(e)}'

    @staticmethod
    def update_variant(product_id: int, variant_id: int, payload: Dict) -> tuple[bool, Optional[Dict], str]:
        try:
            response = requests.put(
                f'{PRODUCT_SERVICE_URL}/products/{product_id}/variants/{variant_id}/',
                json=payload,
                timeout=10,
            )
            if response.status_code == 200:
                return True, response.json(), 'Đã cập nhật biến thể.'
            return False, None, ProductGatewayService._format_product_api_error(response)
        except Exception as e:
            return False, None, f'Loi: {str(e)}'

    @staticmethod
    def list_categories_flat() -> List[Dict]:
        try:
            return _drf_paginated_results(
                f'{PRODUCT_SERVICE_URL}/categories/',
                params={'flat': 'true'},
            )
        except Exception as e:
            print(f"Error fetching categories: {str(e)}")
            return []

    @staticmethod
    def list_brands() -> List[Dict]:
        try:
            return _drf_paginated_results(f'{PRODUCT_SERVICE_URL}/brands/')
        except Exception as e:
            print(f"Error fetching brands: {str(e)}")
            return []

    @staticmethod
    def list_product_types() -> List[Dict]:
        try:
            return _drf_paginated_results(f'{PRODUCT_SERVICE_URL}/product-types/')
        except Exception as e:
            print(f"Error fetching product types: {str(e)}")
            return []


class ProductCatalogGatewayService(ProductGatewayService):
    """Ten service ro nghia theo domain product."""

    pass


class CartGatewayService:
    """Service xử lý logic liên quan đến Cart"""

    @staticmethod
    def _ensure_cart(customer_id: int) -> Optional[Dict]:
        cart_response = requests.get(
            f'{CART_SERVICE_URL}/carts/by_customer/',
            params={'customer_id': customer_id},
            timeout=5,
        )
        if cart_response.status_code == 200:
            return cart_response.json()
        if cart_response.status_code == 404:
            create_response = requests.post(
                f'{CART_SERVICE_URL}/carts/',
                json={'customer_id': customer_id},
                timeout=5,
            )
            if create_response.status_code in [200, 201]:
                return create_response.json()
        return None

    @staticmethod
    def get_cart_by_customer(customer_id: int) -> Optional[Dict]:
        try:
            return CartGatewayService._ensure_cart(customer_id)
        except Exception as e:
            print(f"Error fetching cart for customer {customer_id}: {str(e)}")
            return None

    @staticmethod
    def add_item_to_cart(
        customer_id: int,
        product_id: int,
        quantity: int = 1,
        variant_id: Optional[int] = None,
    ) -> tuple[bool, str]:
        try:
            cart = CartGatewayService._ensure_cart(customer_id)
            if not cart:
                return False, 'Khong tim thay gio hang'
            cart_id = cart['id']
            data = {
                'cart_id': cart_id,
                'book_id': product_id,
                'quantity': quantity,
            }
            if variant_id:
                data['variant_id'] = int(variant_id)
            response = requests.post(f'{CART_SERVICE_URL}/cart-items/', json=data, timeout=5)
            if response.status_code in [200, 201]:
                return True, 'Da them san pham vao gio hang!'
            return False, 'Khong the them san pham vao gio hang'
        except Exception as e:
            return False, f'Loi: {str(e)}'


class OrderGatewayService:
    """Service xử lý logic liên quan đến Order"""

    @staticmethod
    def get_all_orders(customer_id: Optional[int] = None) -> List[Dict]:
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
        try:
            response = requests.post(f'{ORDER_SERVICE_URL}/orders/', json=data, timeout=10)
            if response.status_code == 201:
                order = response.json()
                return True, order, f'Đặt hàng thành công! Mã đơn hàng: #{order["id"]}'
            detail = 'Đặt hàng thất bại'
            try:
                payload = response.json()
                if isinstance(payload, dict) and payload.get('error'):
                    detail = str(payload.get('error'))
            except Exception:
                pass
            return False, None, detail
        except Exception as e:
            return False, None, f'Loi: {str(e)}'


class PaymentGatewayService:
    """Service xử lý logic liên quan đến Payment"""

    @staticmethod
    def get_payment_by_order(order_id: int) -> Optional[Dict]:
        try:
            response = requests.get(
                f'{PAYMENT_SERVICE_URL}/payments/',
                params={'order_id': order_id},
                timeout=5,
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
        try:
            response = requests.get(
                f'{SHIPPING_SERVICE_URL}/shipments/',
                params={'order_id': order_id},
                timeout=5,
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
        try:
            response = requests.get(
                f'{RATING_SERVICE_URL}/ratings/',
                params={'book_id': book_id},
                timeout=5,
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
        try:
            response = requests.get(
                f'{RATING_SERVICE_URL}/ratings/book_stats/',
                params={'book_id': book_id},
                timeout=5,
            )
            if response.status_code == 200:
                return response.json()
            return {}
        except Exception as e:
            print(f"Error fetching stats for book {book_id}: {str(e)}")
            return {}

    @staticmethod
    def add_rating(data: Dict) -> tuple[bool, str]:
        try:
            response = requests.post(f'{RATING_SERVICE_URL}/ratings/', json=data, timeout=5)
            if response.status_code == 201:
                return True, 'Đã thêm đánh giá!'
            error_data = response.json()
            return False, error_data.get('error', 'Không thể thêm đánh giá')
        except Exception as e:
            return False, f'Loi: {str(e)}'

    @staticmethod
    def get_ratings_by_product(product_id: int) -> List[Dict]:
        return RatingGatewayService.get_ratings_by_book(product_id)

    @staticmethod
    def get_product_stats(product_id: int) -> Dict:
        return RatingGatewayService.get_book_stats(product_id)


class RecommendationGatewayService:
    """Service gọi AI recommendation service."""

    @staticmethod
    def get_recommendations(customer_id: int, top_k: int = 8) -> List[int]:
        try:
            response = requests.get(
                f'{RECOMMENDER_SERVICE_URL}/api/recommend',
                params={'user_id': customer_id, 'top_k': top_k},
                timeout=2.5,
            )
            if response.status_code == 200:
                body = response.json()
                return body.get('recommended_products', []) or []
            return []
        except Exception as e:
            print(f"Error fetching recommendations for customer {customer_id}: {str(e)}")
            return []

    @staticmethod
    def track_event(
        *,
        user_id: int,
        session_id: str,
        event_type: str,
        product_id: Optional[int] = None,
        quantity: int = 1,
        source_page: str = '',
    ) -> bool:
        payload = {
            'user_id': user_id,
            'session_id': session_id,
            'event_type': event_type,
            'product_id': product_id,
            'quantity': quantity,
            'source_page': source_page or '',
            'device': 'desktop',
        }
        try:
            response = requests.post(
                f'{RECOMMENDER_SERVICE_URL}/api/tracking/event/',
                json=payload,
                timeout=2.5,
            )
            return response.status_code in [200, 201]
        except Exception as e:
            print(f"Error tracking event {event_type} for user {user_id}: {str(e)}")
            return False

    @staticmethod
    def chat(
        message: str,
        user_id: Optional[int] = None,
        history: Optional[List[Dict[str, str]]] = None,
        include_context: bool = False,
    ) -> tuple[bool, Optional[Dict[str, Any]], str]:
        payload: Dict[str, Any] = {'message': message, 'include_context': include_context}
        if user_id is not None:
            payload['user_id'] = user_id
        if history:
            payload['history'] = history[-10:]
        try:
            response = requests.post(
                f'{RECOMMENDER_SERVICE_URL}/api/chat/',
                json=payload,
                timeout=60,
            )
            if response.status_code == 200:
                return True, response.json(), ''
            return False, None, f'HTTP {response.status_code}: {response.text[:500]}'
        except Exception as e:
            return False, None, str(e)
