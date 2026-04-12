"""
Event collection API views.

Endpoints:
  POST /api/tracking/event/          — single event
  POST /api/tracking/events/batch/   — up to 50 events
"""
import hashlib
import logging

from django.utils import timezone
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import EventLog
from .serializers import EventLogSerializer, BatchEventSerializer
from .throttles import EventCollectorThrottle

logger = logging.getLogger(__name__)


def _compute_hash(data: dict) -> str:
    """SHA-256 hash of (user_id, session_id, event_type, product_id, timestamp-to-second)."""
    ts_str = data['timestamp'].replace(microsecond=0).isoformat()
    raw = (
        f"{data['user_id']}|{data['session_id']}|{data['event_type']}|"
        f"{data.get('product_id', '')}|{ts_str}"
    )
    return hashlib.sha256(raw.encode('utf-8')).hexdigest()


def _save_event(data: dict) -> tuple[EventLog | None, str]:
    """
    Persist a single validated event dict.
    Returns (EventLog | None, status_str)
    """
    event_hash = _compute_hash(data)
    try:
        event, created = EventLog.objects.get_or_create(
            event_hash=event_hash,
            defaults={
                'user_id': data['user_id'],
                'session_id': data['session_id'],
                'event_type': data['event_type'],
                'product_id': data.get('product_id'),
                'category_id': data.get('category_id'),
                'brand_id': data.get('brand_id'),
                'timestamp': data['timestamp'],
                'device': data.get('device', 'unknown'),
                'source_page': data.get('source_page', ''),
                'keyword': data.get('keyword', ''),
                'quantity': data.get('quantity', 1),
                'price': data.get('price'),
            },
        )
        if not created:
            logger.debug('Duplicate event skipped hash=%s', event_hash[:8])
            return event, 'duplicate'
        logger.info(
            'Event saved event_type=%s user_id=%s product_id=%s',
            data['event_type'], data['user_id'], data.get('product_id'),
        )
        return event, 'ok'
    except Exception as exc:
        logger.error('Error saving event: %s', exc, exc_info=True)
        return None, 'error'


class EventCollectorView(APIView):
    """
    POST /api/tracking/event/

    Accepts a single user behaviour event.
    Returns 201 Created on success, 200 OK if duplicate, 400 on validation error.

    Example payload:
    {
        "user_id": 42,
        "session_id": "sess_abc123",
        "event_type": "product_view",
        "product_id": 55,
        "category_id": 3,
        "brand_id": 7,
        "device": "mobile",
        "source_page": "/san-pham/55"
    }
    """
    throttle_classes = [EventCollectorThrottle]

    def post(self, request):
        serializer = EventLogSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(
                {'errors': serializer.errors},
                status=status.HTTP_400_BAD_REQUEST,
            )

        data = serializer.validated_data
        event, result_status = _save_event(data)

        if result_status == 'error':
            return Response({'status': 'error'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        if result_status == 'duplicate':
            return Response({'status': 'duplicate'}, status=status.HTTP_200_OK)

        return Response(
            {'status': 'ok', 'id': event.id},
            status=status.HTTP_201_CREATED,
        )


class BatchEventCollectorView(APIView):
    """
    POST /api/tracking/events/batch/

    Accepts up to 50 events in one request.
    Reduces HTTP overhead for active browsing sessions.
    Returns HTTP 207 Multi-Status with per-event results.

    Example payload:
    {
        "events": [
            {"user_id": 1, "session_id": "s1", "event_type": "product_view", "product_id": 55},
            {"user_id": 1, "session_id": "s1", "event_type": "add_to_cart", "product_id": 55}
        ]
    }
    """
    throttle_classes = [EventCollectorThrottle]

    def post(self, request):
        serializer = BatchEventSerializer(data=request.data)
        if not serializer.is_valid():
            return Response({'errors': serializer.errors}, status=status.HTTP_400_BAD_REQUEST)

        results = []
        for event_data in serializer.validated_data['events']:
            event, result_status = _save_event(event_data)
            results.append({
                'status': result_status,
                'id': event.id if event and result_status == 'ok' else None,
            })

        success_count = sum(1 for r in results if r['status'] == 'ok')
        logger.info('Batch ingestion: %d/%d events saved', success_count, len(results))

        return Response({'results': results}, status=status.HTTP_207_MULTI_STATUS)
