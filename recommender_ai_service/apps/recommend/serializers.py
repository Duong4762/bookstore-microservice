"""Serializers for the recommend app."""
from rest_framework import serializers


class RecommendRequestSerializer(serializers.Serializer):
    """
    POST /api/recommend/

    Minimal request: {"user_id": 123}
    Full request with pre-fetched events:
    {
        "user_id": 123,
        "top_k": 5,
        "exclude_products": [11, 22],
        "recent_events": [
            {"event_type": "product_view", "product_id": 55, "category_id": 3, "brand_id": 7},
            {"event_type": "add_to_cart",  "product_id": 55, "category_id": 3, "brand_id": 7}
        ]
    }
    """

    class RecentEventSerializer(serializers.Serializer):
        event_type = serializers.CharField(max_length=20)
        product_id = serializers.IntegerField(min_value=1, required=False, allow_null=True)
        category_id = serializers.IntegerField(min_value=1, required=False, allow_null=True)
        brand_id = serializers.IntegerField(min_value=1, required=False, allow_null=True)

    user_id = serializers.IntegerField(min_value=1)
    top_k = serializers.IntegerField(min_value=1, max_value=20, required=False, default=5)
    exclude_products = serializers.ListField(
        child=serializers.IntegerField(min_value=1),
        required=False,
        default=list,
        max_length=50,
    )
    recent_events = serializers.ListField(
        child=RecentEventSerializer(),
        required=False,
        default=None,
        allow_null=True,
        max_length=50,
    )
