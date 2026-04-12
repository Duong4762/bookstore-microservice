from django.db import models
from django.core.validators import EmailValidator


class Customer(models.Model):
    """Model đại diện cho khách hàng trong hệ thống"""
    
    email = models.EmailField(unique=True, validators=[EmailValidator()])
    full_name = models.CharField(max_length=255)
    phone_number = models.CharField(max_length=20, blank=True, null=True)
    address = models.TextField(blank=True, null=True)
    date_of_birth = models.DateField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    is_active = models.BooleanField(default=True)
    
    class Meta:
        db_table = 'customers'
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.full_name} ({self.email})"
