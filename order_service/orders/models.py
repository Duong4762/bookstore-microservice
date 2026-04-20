from django.db import models


class Order(models.Model):
    """Model đại diện cho đơn hàng"""
    
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('paid', 'Paid'),
        ('shipped', 'Shipped'),
        ('delivered', 'Delivered'),
        ('cancelled', 'Cancelled'),
    ]
    
    customer_id = models.IntegerField()  # ID của customer từ Customer Service
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    total_amount = models.DecimalField(max_digits=14, decimal_places=2)
    shipping_address = models.TextField()
    phone_number = models.CharField(max_length=20)
    notes = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'orders'
        ordering = ['-created_at']
    
    def __str__(self):
        return f"Order #{self.id} - Customer {self.customer_id}"


class OrderItem(models.Model):
    """Model đại diện cho một sản phẩm trong đơn hàng"""
    
    order = models.ForeignKey(Order, related_name='items', on_delete=models.CASCADE)
    book_id = models.IntegerField()  # ID của book từ Book Service
    quantity = models.IntegerField(default=1)
    price = models.DecimalField(max_digits=14, decimal_places=2)  # Giá tại thời điểm đặt hàng
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'order_items'
        ordering = ['-created_at']
    
    def __str__(self):
        return f"OrderItem {self.id} - Order {self.order.id}"
    
    @property
    def subtotal(self):
        """Tổng tiền của item này"""
        return self.price * self.quantity
