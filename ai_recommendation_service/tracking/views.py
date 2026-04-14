"""Event collection — mỗi sự kiện mới có thể cập nhật cạnh đồ thị (incremental)."""
import hashlib
import logging

from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from recommendation.services.realtime_graph import on_event_logged
from recommendation.services.retrain_runtime import notify_new_events

from .models import EventLog
from .serializers import BatchEventSerializer, EventLogSerializer
from .throttles import EventCollectorThrottle

logger = logging.getLogger(__name__)


def _compute_hash(data: dict) -> str:
    ts_str = data['timestamp'].replace(microsecond=0).isoformat()
    raw = (
        f"{data['user_id']}|{data['session_id']}|{data['event_type']}|"
        f"{data.get('product_id', '')}|{ts_str}"
    )
    return hashlib.sha256(raw.encode('utf-8')).hexdigest()


def _save_event(data: dict) -> tuple[EventLog | None, str]:
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
    throttle_classes = [EventCollectorThrottle]

    def post(self, request):
        serializer = EventLogSerializer(data=request.data)
        if not serializer.is_valid():
            return Response({'errors': serializer.errors}, status=status.HTTP_400_BAD_REQUEST)

        data = serializer.validated_data
        event, result_status = _save_event(data)

        if result_status == 'error':
            return Response({'status': 'error'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        if result_status == 'duplicate':
            return Response({'status': 'duplicate'}, status=status.HTTP_200_OK)

        on_event_logged(event)
        notify_new_events(1)
        return Response({'status': 'ok', 'id': event.id}, status=status.HTTP_201_CREATED)


class BatchEventCollectorView(APIView):
    throttle_classes = [EventCollectorThrottle]

    def post(self, request):
        serializer = BatchEventSerializer(data=request.data)
        if not serializer.is_valid():
            return Response({'errors': serializer.errors}, status=status.HTTP_400_BAD_REQUEST)

        results = []
        for event_data in serializer.validated_data['events']:
            event, result_status = _save_event(event_data)
            if result_status == 'ok' and event:
                on_event_logged(event)
            results.append({
                'status': result_status,
                'id': event.id if event and result_status == 'ok' else None,
            })

        success_count = sum(1 for r in results if r['status'] == 'ok')
        if success_count:
            notify_new_events(success_count)
        logger.info('Batch ingestion: %d/%d events saved', success_count, len(results))

        return Response({'results': results}, status=status.HTTP_207_MULTI_STATUS)
