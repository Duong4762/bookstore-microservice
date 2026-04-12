"""
Service layer for Payment business logic
"""
import requests
from typing import Optional
from django.utils import timezone
from .models import Payment
from .serializers import PaymentSerializer


class PaymentService:
    """Service class xử lý business logic cho Payment"""
    
    ORDER_SERVICE_URL = 'http://localhost:8004/api/orders'
    
    @staticmethod
    def create_payment(order_id: int, amount: float, payment_method: str) -> Payment:
        """
        Tạo payment mới
        
        Args:
            order_id: ID của order
            amount: Số tiền
            payment_method: Phương thức thanh toán
            
        Returns:
            Payment object đã tạo
        """
        payment = Payment.objects.create(
            order_id=order_id,
            amount=amount,
            payment_method=payment_method
        )
        return payment
    
    @staticmethod
    def get_payments_by_order(order_id: Optional[int] = None):
        """Lấy danh sách payments, có thể lọc theo order_id"""
        if order_id:
            return Payment.objects.filter(order_id=order_id)
        return Payment.objects.all()
    
    @staticmethod
    def get_payment_by_id(payment_id: int) -> Optional[Payment]:
        """Lấy payment theo ID"""
        try:
            return Payment.objects.get(id=payment_id)
        except Payment.DoesNotExist:
            return None
    
    @staticmethod
    def process_payment(payment_id: int, transaction_id: str = "", notes: str = "") -> Optional[Payment]:
        """
        Xử lý thanh toán - đánh dấu payment là completed
        
        Args:
            payment_id: ID của payment
            transaction_id: Mã giao dịch
            notes: Ghi chú
            
        Returns:
            Payment object đã cập nhật hoặc None
        """
        payment = PaymentService.get_payment_by_id(payment_id)
        if not payment or payment.status == 'completed':
            return None
        
        payment.status = 'completed'
        payment.payment_date = timezone.now()
        payment.transaction_id = transaction_id
        payment.notes = notes
        payment.save()
        
        # Cập nhật order status sang 'paid'
        PaymentService._update_order_status(payment.order_id, 'paid')
        
        return payment
    
    @staticmethod
    def _update_order_status(order_id: int, new_status: str) -> None:
        """Cập nhật status của order"""
        try:
            requests.patch(
                f'{PaymentService.ORDER_SERVICE_URL}/{order_id}/',
                json={'status': new_status},
                timeout=5
            )
        except Exception as e:
            print(f"Error updating order {order_id} status: {str(e)}")
    
    @staticmethod
    def refund_payment(payment_id: int) -> Optional[Payment]:
        """Hoàn tiền"""
        payment = PaymentService.get_payment_by_id(payment_id)
        if not payment or payment.status != 'completed':
            return None
        
        payment.status = 'refunded'
        payment.save()
        return payment
