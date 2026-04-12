"""
Service layer for Shipping business logic
"""
import uuid
import requests
from typing import Optional
from django.utils import timezone
from .models import Shipment
from .serializers import ShipmentSerializer


class ShipmentService:
    """Service class xử lý business logic cho Shipment"""
    
    ORDER_SERVICE_URL = 'http://localhost:8004/api/orders'
    
    @staticmethod
    def create_shipment(order_id: int, shipping_address: str, 
                       carrier: str = "", estimated_delivery=None) -> Shipment:
        """
        Tạo shipment mới
        
        Args:
            order_id: ID của order
            shipping_address: Địa chỉ giao hàng
            carrier: Đơn vị vận chuyển
            estimated_delivery: Thời gian dự kiến giao hàng
            
        Returns:
            Shipment object đã tạo
        """
        tracking_number = f"TRK-{uuid.uuid4().hex[:12].upper()}"
        
        shipment = Shipment.objects.create(
            order_id=order_id,
            tracking_number=tracking_number,
            carrier=carrier,
            shipping_address=shipping_address,
            estimated_delivery=estimated_delivery
        )
        return shipment
    
    @staticmethod
    def get_shipments_by_order(order_id: Optional[int] = None):
        """Lấy danh sách shipments, có thể lọc theo order_id"""
        if order_id:
            return Shipment.objects.filter(order_id=order_id)
        return Shipment.objects.all()
    
    @staticmethod
    def get_shipment_by_id(shipment_id: int) -> Optional[Shipment]:
        """Lấy shipment theo ID"""
        try:
            return Shipment.objects.get(id=shipment_id)
        except Shipment.DoesNotExist:
            return None
    
    @staticmethod
    def get_shipment_by_tracking(tracking_number: str) -> Optional[Shipment]:
        """Lấy shipment theo tracking number"""
        try:
            return Shipment.objects.get(tracking_number=tracking_number)
        except Shipment.DoesNotExist:
            return None
    
    @staticmethod
    def update_shipment_status(shipment_id: int, new_status: str) -> Optional[Shipment]:
        """
        Cập nhật trạng thái shipment
        
        Args:
            shipment_id: ID của shipment
            new_status: Trạng thái mới
            
        Returns:
            Shipment object đã cập nhật hoặc None
        """
        shipment = ShipmentService.get_shipment_by_id(shipment_id)
        if not shipment:
            return None
        
        old_status = shipment.status
        shipment.status = new_status
        
        # Nếu status là delivered, cập nhật actual_delivery
        if new_status == 'delivered' and old_status != 'delivered':
            shipment.actual_delivery = timezone.now()
            ShipmentService._update_order_status(shipment.order_id, 'delivered')
        
        shipment.save()
        return shipment
    
    @staticmethod
    def start_shipping(shipment_id: int) -> Optional[Shipment]:
        """Bắt đầu vận chuyển"""
        shipment = ShipmentService.get_shipment_by_id(shipment_id)
        if not shipment or shipment.status != 'preparing':
            return None
        
        shipment.status = 'shipping'
        shipment.save()
        
        ShipmentService._update_order_status(shipment.order_id, 'shipped')
        return shipment
    
    @staticmethod
    def _update_order_status(order_id: int, new_status: str) -> None:
        """Cập nhật status của order"""
        try:
            requests.patch(
                f'{ShipmentService.ORDER_SERVICE_URL}/{order_id}/',
                json={'status': new_status},
                timeout=5
            )
        except Exception as e:
            print(f"Error updating order {order_id} status: {str(e)}")
