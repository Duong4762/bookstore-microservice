from django.db import models


class Cart(models.Model):
    """Model đại diện cho giỏ hàng của khách hàng"""
    
    customer_id = models.IntegerField(unique=True)  # ID của customer từ Customer Service
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'carts'
        ordering = ['-created_at']
    
    def __str__(self):
        return f"Cart for customer {self.customer_id}"
    
    @property
    def total_items(self):
        """Tổng số sản phẩm trong giỏ hàng"""
        return sum(item.quantity for item in self.items.all())
    
    @property
    def total_price(self):
        """Tổng giá trị giỏ hàng"""
        return sum(item.subtotal for item in self.items.all())


class CartItem(models.Model):
    """Model đại diện cho một sản phẩm trong giỏ hàng"""
    
    cart = models.ForeignKey(Cart, related_name='items', on_delete=models.CASCADE)
    book_id = models.IntegerField()  # ID của book từ Book Service
    quantity = models.IntegerField(default=1)
    price = models.DecimalField(max_digits=10, decimal_places=2)  # Giá tại thời điểm thêm vào
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'cart_items'
        unique_together = ['cart', 'book_id']
        ordering = ['-created_at']
    
    def __str__(self):
        return f"CartItem {self.id} - Book {self.book_id}"
    
    @property
    def subtotal(self):
        """Tổng tiền của item này"""
        return self.price * self.quantity
