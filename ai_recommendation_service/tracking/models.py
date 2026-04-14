"""EventLog — user behaviour for knowledge graph construction."""
from django.db import models


class EventLog(models.Model):
    """Raw user behaviour event."""

    class EventType(models.TextChoices):
        PRODUCT_VIEW = 'product_view', 'Product View'
        PRODUCT_CLICK = 'product_click', 'Product Click'
        ADD_TO_CART = 'add_to_cart', 'Add to Cart'
        PURCHASE = 'purchase', 'Purchase'
        SEARCH = 'search', 'Search'

    user_id = models.IntegerField(db_index=True)
    session_id = models.CharField(max_length=64, db_index=True)
    event_type = models.CharField(max_length=20, choices=EventType.choices, db_index=True)
    product_id = models.IntegerField(null=True, blank=True, db_index=True)
    category_id = models.IntegerField(null=True, blank=True)
    brand_id = models.IntegerField(null=True, blank=True)
    timestamp = models.DateTimeField(db_index=True)
    device = models.CharField(max_length=20, blank=True, default='')
    source_page = models.CharField(max_length=200, blank=True, default='')
    keyword = models.CharField(max_length=255, blank=True, default='')
    quantity = models.PositiveSmallIntegerField(default=1)
    price = models.DecimalField(max_digits=14, decimal_places=2, null=True, blank=True)
    event_hash = models.CharField(max_length=64, unique=True, db_index=True)
    received_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        indexes = [
            models.Index(fields=['user_id', 'timestamp']),
            models.Index(fields=['event_type', 'timestamp']),
            models.Index(fields=['product_id', 'event_type']),
        ]
        ordering = ['timestamp']

    def __str__(self):
        return f'[{self.event_type}] user={self.user_id} product={self.product_id}'
