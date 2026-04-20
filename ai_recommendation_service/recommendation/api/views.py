"""REST API: recommend, retrain, bestsellers, invalidate cache."""
from __future__ import annotations

import logging
import time

from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from catalog_proxy.client import get_products_bulk

from ..services.cold_start import popular_product_ids
from ..services.chat_rag import chat_with_rag
from ..services.embedding_cache import UserEmbeddingCache
from ..services.inference import RecommendEngine
from ..services.retrain_runtime import retrain_status, trigger_retrain_async

from .serializers import (
    ChatMessageSerializer,
    InvalidateSerializer,
    RecommendPostSerializer,
    RecommendQuerySerializer,
)

logger = logging.getLogger(__name__)


class RecommendGetView(APIView):
    """
    GET /api/recommend?user_id=1&top_k=10
    """

    def get(self, request):
        ser = RecommendQuerySerializer(data=request.query_params)
        if not ser.is_valid():
            return Response({'errors': ser.errors}, status=status.HTTP_400_BAD_REQUEST)
        d = ser.validated_data
        user_id = d['user_id']
        top_k = d.get('top_k', 10)
        enrich = d.get('enrich', False)

        t0 = time.perf_counter()
        try:
            pids, source, _ = RecommendEngine.instance().recommend(user_id, top_k=top_k)
        except Exception as exc:
            logger.error('recommend error: %s', exc, exc_info=True)
            return Response({'error': 'internal_error'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        latency_ms = round((time.perf_counter() - t0) * 1000, 2)
        body = {
            'user_id': user_id,
            'recommended_products': pids,
            'source': source,
            'latency_ms': latency_ms,
        }
        if enrich:
            body['products'] = get_products_bulk(pids)
        return Response(body)


class RecommendPostCompatView(APIView):
    """
    POST /api/recommend/  (body JSON giống service cũ)
    """

    def post(self, request):
        ser = RecommendPostSerializer(data=request.data)
        if not ser.is_valid():
            return Response({'errors': ser.errors}, status=status.HTTP_400_BAD_REQUEST)
        d = ser.validated_data
        user_id = d['user_id']
        top_k = d.get('top_k', 10)
        exclude = d.get('exclude_products') or []
        enrich = d.get('enrich', False)

        t0 = time.perf_counter()
        try:
            pids, source, _ = RecommendEngine.instance().recommend(
                user_id, top_k=top_k, exclude_products=exclude
            )
        except Exception as exc:
            logger.error('recommend error: %s', exc, exc_info=True)
            return Response({'error': 'internal_error'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        latency_ms = round((time.perf_counter() - t0) * 1000, 2)
        body = {
            'user_id': user_id,
            'recommended_products': pids,
            'source': source,
            'latency_ms': latency_ms,
        }
        if enrich:
            body['products'] = get_products_bulk(pids)
        return Response(body)


class RetrainView(APIView):
    """POST /api/recommend/retrain — chạy pipeline nền (thread)."""

    def post(self, request):
        if not trigger_retrain_async(trigger='manual_api'):
            return Response(
                {'status': 'already_running', 'detail': 'Pipeline đang chạy'},
                status=status.HTTP_409_CONFLICT,
            )
        return Response({'status': 'started', 'message': 'Đã khởi chạy huấn luyện lại BiLSTM'}, status=status.HTTP_202_ACCEPTED)


class RetrainStatusView(APIView):
    """GET /api/recommend/retrain/status"""

    def get(self, request):
        return Response(retrain_status())


class BestSellersView(APIView):
    def get(self, request):
        top_k = int(request.query_params.get('top_k', 10))
        top_k = min(max(top_k, 1), 50)
        return Response({'bestseller_products': popular_product_ids(top_k)})


class InvalidateCacheView(APIView):
    def post(self, request):
        ser = InvalidateSerializer(data=request.data)
        if not ser.is_valid():
            return Response({'errors': ser.errors}, status=status.HTTP_400_BAD_REQUEST)
        uid = ser.validated_data['user_id']
        UserEmbeddingCache.invalidate(uid)
        return Response({'status': 'ok', 'user_id': uid})


class ChatRagView(APIView):
    """POST /api/chat/ — Gemini + retrieval from catalog + recommendation."""

    def post(self, request):
        ser = ChatMessageSerializer(data=request.data)
        if not ser.is_valid():
            return Response({'errors': ser.errors}, status=status.HTTP_400_BAD_REQUEST)
        data = ser.validated_data
        clean_history = []
        for h in (data.get('history') or [])[-10:]:
            if not isinstance(h, dict):
                continue
            role = (h.get('role') or '').strip()
            content = (h.get('content') or '').strip()
            if role in ('user', 'assistant') and content:
                clean_history.append({'role': role, 'content': content[:4000]})
        try:
            out = chat_with_rag(
                message=data['message'].strip(),
                user_id=data.get('user_id'),
                history=clean_history,
                include_context=bool(data.get('include_context')),
            )
            return Response(out)
        except Exception as exc:
            logger.error('chat rag failed: %s', exc, exc_info=True)
            return Response({'error': 'chat_failed'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
