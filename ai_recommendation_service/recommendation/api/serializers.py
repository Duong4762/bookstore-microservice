from rest_framework import serializers


class RecommendQuerySerializer(serializers.Serializer):
    user_id = serializers.IntegerField(min_value=1)
    top_k = serializers.IntegerField(min_value=1, max_value=100, default=10, required=False)
    enrich = serializers.BooleanField(default=False, required=False)


class RecommendPostSerializer(serializers.Serializer):
    """Tương thích client cũ POST /api/recommend/"""

    user_id = serializers.IntegerField(min_value=1)
    top_k = serializers.IntegerField(min_value=1, max_value=100, default=10, required=False)
    exclude_products = serializers.ListField(
        child=serializers.IntegerField(min_value=1), required=False, default=list,
    )
    enrich = serializers.BooleanField(default=False, required=False)


class InvalidateSerializer(serializers.Serializer):
    user_id = serializers.IntegerField(min_value=1)
