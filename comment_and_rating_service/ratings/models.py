from django.db import models
from django.core.validators import MinValueValidator, MaxValueValidator


class Rating(models.Model):
    """Model đại diện cho đánh giá và nhận xét của khách hàng về sách"""
    
    book_id = models.IntegerField()  # ID của book từ Book Service
    customer_id = models.IntegerField()  # ID của customer từ Customer Service
    rating = models.IntegerField(
        validators=[MinValueValidator(1), MaxValueValidator(5)],
        help_text="Rating từ 1 đến 5 sao"
    )
    comment = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'ratings'
        ordering = ['-created_at']
        unique_together = ['book_id', 'customer_id']  # Một customer chỉ đánh giá 1 sách 1 lần
    
    def __str__(self):
        return f"Rating {self.rating} for Book {self.book_id} by Customer {self.customer_id}"
