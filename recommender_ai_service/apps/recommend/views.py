"""
Recommendation API views.

POST /api/recommend/  →  RecommendView
GET  /api/recommend/bestsellers/  →  BestSellersView
"""
import logging
import time

from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from .serializers import RecommendRequestSerializer
from .services import RecommendationService

logger = logging.getLogger(__name__)

_service = RecommendationService()  # module-level singleton, reused across requests


class RecommendView(APIView):
    """
    POST /api/recommend/

    Returns top-K recommended product IDs for a user.

    Request:
        {"user_id": 123}

    Response:
        {
            "user_id": 123,
            "recommended_products": [55, 89, 34, 21, 77],
            "source": "ml_model",   // "ml_model" | "bestsellers" | "cached"
            "latency_ms": 12
        }
    """

    def post(self, request):
        t0 = time.perf_counter()

        serializer = RecommendRequestSerializer(data=request.data)
        if not serializer.is_valid():
            return Response({'errors': serializer.errors}, status=status.HTTP_400_BAD_REQUEST)

        data = serializer.validated_data
        user_id = data['user_id']
        top_k = data['top_k']
        exclude_products = data.get('exclude_products') or []
        recent_events = data.get('recent_events')

        try:
            recommendations = _service.get_recommendations(
                user_id=user_id,
                recent_events=recent_events,
                top_k=top_k,
                exclude_products=exclude_products,
            )
        except Exception as exc:
            logger.error('Unexpected recommend error for user=%s: %s', user_id, exc, exc_info=True)
            return Response(
                {'error': 'Internal server error'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

        latency_ms = round((time.perf_counter() - t0) * 1000, 1)
        logger.info(
            'Recommend user=%s top=%d results=%d latency=%.1fms',
            user_id, top_k, len(recommendations), latency_ms,
        )

        return Response({
            'user_id': user_id,
            'recommended_products': recommendations,
            'latency_ms': latency_ms,
        })


class BestSellersView(APIView):
    """
    GET /api/recommend/bestsellers/

    Returns globally computed bestseller products (cold start pool).
    Useful for homepage "trending" sections.
    """

    def get(self, request):
        top_k = int(request.query_params.get('top_k', 10))
        top_k = min(max(top_k, 1), 50)

        bestsellers = _service.cache.get_bestsellers()
        if not bestsellers:
            bestsellers = _service._compute_bestsellers()
            if bestsellers:
                _service.cache.set_bestsellers(bestsellers)

        return Response({
            'bestseller_products': bestsellers[:top_k],
        })


class InvalidateCacheView(APIView):
    """
    POST /api/recommend/invalidate/

    Force-invalidate a user's recommendation cache (e.g. after checkout).
    Body: {"user_id": 123}
    """

    def post(self, request):
        user_id = request.data.get('user_id')
        if not user_id:
            return Response({'error': 'user_id required'}, status=status.HTTP_400_BAD_REQUEST)
        _service.invalidate_user_cache(int(user_id))
        return Response({'status': 'ok', 'user_id': user_id})
