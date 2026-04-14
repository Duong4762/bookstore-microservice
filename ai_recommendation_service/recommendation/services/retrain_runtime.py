"""Runtime retrain state + background execution shared by API/scheduler."""
from __future__ import annotations

import logging
import threading
from typing import Any, Dict
from django.conf import settings

logger = logging.getLogger(__name__)

_retrain_lock = threading.Lock()
_event_lock = threading.Lock()
_pending_event_count = 0
_retrain_status: Dict[str, Any] = {
    'running': False,
    'last_result': None,
    'last_error': None,
    'last_trigger': None,
}


def _event_threshold() -> int:
    return int(settings.RECOMMENDATION_ML.get('AUTO_RETRAIN_EVENT_THRESHOLD', 10))


def _try_trigger_from_pending(trigger: str = 'event_threshold') -> bool:
    """Try trigger retrain if pending events reached threshold."""
    global _pending_event_count
    threshold = max(1, _event_threshold())
    with _event_lock:
        if _pending_event_count < threshold:
            return False
    started = trigger_retrain_async(trigger=trigger)
    if started:
        with _event_lock:
            _pending_event_count = max(0, _pending_event_count - threshold)
        logger.info('Auto retrain triggered by event threshold (threshold=%s)', threshold)
    return started


def _run_retrain_bg(trigger: str) -> None:
    try:
        from .trainer import run_full_training_pipeline

        result = run_full_training_pipeline()
        _retrain_status['last_result'] = result
        _retrain_status['last_error'] = None
        _retrain_status['last_trigger'] = trigger
        from .inference import RecommendEngine

        RecommendEngine.reload()
        logger.info('Retrain done (trigger=%s): %s', trigger, result)
    except Exception as exc:
        _retrain_status['last_error'] = str(exc)
        _retrain_status['last_trigger'] = trigger
        logger.exception('Retrain failed (trigger=%s)', trigger)
    finally:
        _retrain_status['running'] = False
        # Catch up: nếu trong lúc train có thêm >= threshold events thì train tiếp vòng sau.
        _try_trigger_from_pending(trigger='event_threshold_catchup')


def trigger_retrain_async(trigger: str = 'manual_api') -> bool:
    """Return True if started, False if already running."""
    with _retrain_lock:
        if _retrain_status['running']:
            return False
        _retrain_status['running'] = True
    threading.Thread(target=_run_retrain_bg, args=(trigger,), daemon=True).start()
    return True


def notify_new_events(count: int = 1) -> bool:
    """
    Notify runtime about newly ingested events.
    Returns True if this call starts a retrain.
    """
    global _pending_event_count
    if count <= 0:
        return False
    with _event_lock:
        _pending_event_count += count
    return _try_trigger_from_pending(trigger='event_threshold')


def retrain_status() -> Dict[str, Any]:
    with _event_lock:
        pending = _pending_event_count
    status = dict(_retrain_status)
    status['pending_events'] = pending
    status['event_threshold'] = max(1, _event_threshold())
    return status
