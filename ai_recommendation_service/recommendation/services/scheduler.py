"""In-process scheduler for periodic retraining (no Celery)."""
from __future__ import annotations

import logging
import os
import threading
import time

from django.conf import settings

from .retrain_runtime import trigger_retrain_async

logger = logging.getLogger(__name__)

_started = False
_lock = threading.Lock()


def _enabled() -> bool:
    return bool(settings.RECOMMENDATION_ML.get('AUTO_RETRAIN_ENABLED', False))


def _interval_seconds() -> int:
    return int(settings.RECOMMENDATION_ML.get('AUTO_RETRAIN_INTERVAL_SECONDS', 3600))


def _loop() -> None:
    interval = max(60, _interval_seconds())
    logger.info('Auto-retrain scheduler started (interval=%ss)', interval)
    while True:
        time.sleep(interval)
        started = trigger_retrain_async(trigger='daily_scheduler')
        if started:
            logger.info('Auto-retrain kicked off.')
        else:
            logger.info('Skip auto-retrain: previous retrain still running.')


def start_scheduler_if_needed() -> None:
    global _started
    if not _enabled():
        return
    # runserver autoreload creates parent+child; only run in child process
    run_main = os.environ.get('RUN_MAIN')
    if run_main is not None and run_main.lower() != 'true':
        return
    with _lock:
        if _started:
            return
        _started = True
    threading.Thread(target=_loop, daemon=True).start()
