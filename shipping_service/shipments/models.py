from django.db import models


class Shipment(models.Model):
    """Model đại diện cho đơn vận chuyển"""
    
    STATUS_CHOICES = [
        ('preparing', 'Preparing'),
        ('shipping', 'Shipping'),
        ('delivered', 'Delivered'),
        ('returned', 'Returned'),
        ('cancelled', 'Cancelled'),
    ]
    
    order_id = models.IntegerField(unique=True)  # ID của order từ Order Service
    tracking_number = models.CharField(max_length=100, unique=True, blank=True, null=True)
    carrier = models.CharField(max_length=100, blank=True, null=True)  # Đơn vị vận chuyển
    shipping_address = models.TextField()
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='preparing')
    estimated_delivery = models.DateTimeField(blank=True, null=True)
    actual_delivery = models.DateTimeField(blank=True, null=True)
    notes = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'shipments'
        ordering = ['-created_at']
    
    def __str__(self):
        return f"Shipment for Order #{self.order_id} - {self.status}"
