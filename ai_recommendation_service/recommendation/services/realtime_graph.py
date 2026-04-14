"""Singleton GraphBuilder + hook sau khi ghi log."""
from __future__ import annotations

import logging
import threading
from typing import TYPE_CHECKING, Optional

if TYPE_CHECKING:
    from tracking.models import EventLog

    from .graph_builder import GraphBuilder

logger = logging.getLogger(__name__)
_lock = threading.RLock()
_builder: Optional['GraphBuilder'] = None


def get_graph_builder() -> 'GraphBuilder':
    """Lazy singleton — dùng chung cho incremental update và pipeline offline."""
    global _builder
    with _lock:
        if _builder is None:
            from django.conf import settings

            from .graph_builder import GraphBuilder
            from .graph_storage import NetworkXGraphStorage

            _builder = GraphBuilder(NetworkXGraphStorage())
            p = settings.RECOMMENDATION_ML['GRAPH_PICKLE_PATH']
            try:
                if p.exists():
                    _builder.load(str(p))
            except Exception as exc:
                logger.warning('Could not load graph pickle: %s', exc)
        return _builder


def reset_graph_builder() -> None:
    """Sau retrain: tạo instance mới hoặc reload pickle."""
    global _builder
    with _lock:
        _builder = None


def on_event_logged(event: 'EventLog') -> None:
    try:
        get_graph_builder().apply_event(event)
        from .embedding_cache import UserEmbeddingCache

        UserEmbeddingCache.invalidate(event.user_id)
    except Exception as exc:
        logger.warning('Incremental graph update skipped: %s', exc)
