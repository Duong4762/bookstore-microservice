from django.utils import timezone
from rest_framework import serializers

from recommendation.services.product_groups import ALL_PRODUCT_IDS

from .models import EventLog

VALID_DEVICES = {'desktop', 'mobile', 'tablet', 'unknown'}


class EventLogSerializer(serializers.Serializer):
    user_id = serializers.IntegerField(min_value=1)
    session_id = serializers.CharField(max_length=64)
    event_type = serializers.ChoiceField(choices=EventLog.EventType.values)
    product_id = serializers.IntegerField(min_value=1, required=False, allow_null=True, default=None)
    category_id = serializers.IntegerField(min_value=1, required=False, allow_null=True, default=None)
    brand_id = serializers.IntegerField(min_value=1, required=False, allow_null=True, default=None)
    timestamp = serializers.DateTimeField(required=False, default=None)
    device = serializers.CharField(max_length=20, required=False, default='unknown')
    source_page = serializers.CharField(max_length=200, required=False, default='', allow_blank=True)
    keyword = serializers.CharField(max_length=255, required=False, default='', allow_blank=True)
    quantity = serializers.IntegerField(min_value=1, max_value=9999, required=False, default=1)
    price = serializers.DecimalField(
        max_digits=14, decimal_places=2, required=False, allow_null=True, default=None, min_value=0,
    )

    def validate_device(self, value):
        return value.lower() if value.lower() in VALID_DEVICES else 'unknown'

    def validate_product_id(self, value):
        if value is None:
            return value
        if value not in ALL_PRODUCT_IDS:
            raise serializers.ValidationError('product_id must belong to configured product groups (1..300).')
        return value

    def validate(self, attrs):
        if attrs['event_type'] in ('product_view', 'product_click', 'add_to_cart', 'purchase'):
            if not attrs.get('product_id'):
                raise serializers.ValidationError(
                    {'product_id': f'product_id is required for event_type={attrs["event_type"]}'}
                )
        if not attrs.get('timestamp'):
            attrs['timestamp'] = timezone.now()
        return attrs


class BatchEventSerializer(serializers.Serializer):
    events = serializers.ListField(child=EventLogSerializer(), min_length=1, max_length=50)
