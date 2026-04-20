"""BiLSTM inference engine for recommendation."""
from __future__ import annotations

import json
import logging
import os
import threading
import time
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple

import numpy as np
from django.conf import settings
from tensorflow.keras.models import load_model
from tensorflow.keras.preprocessing.sequence import pad_sequences

from tracking.models import EventLog

from .cold_start import cold_start_recommendations, popular_product_ids
from .trainer import ACTION_ID_MAP, EVENT_TO_ACTION

logger = logging.getLogger(__name__)


class RecommendEngine:
    _instance: Optional['RecommendEngine'] = None
    _lock = threading.RLock()

    def __init__(self) -> None:
        self._ready = False
        self._load_error: Optional[str] = None
        self._skip = False
        self.model: Optional[Any] = None
        self.max_len = 10
        self.product_classes: List[int] = []
        self.product_to_encoded: Dict[int, int] = {}

    @classmethod
    def instance(cls) -> 'RecommendEngine':
        with cls._lock:
            if cls._instance is None:
                cls._instance = RecommendEngine()
                cls._instance._try_load()
            return cls._instance

    @classmethod
    def reload(cls) -> None:
        with cls._lock:
            cls._instance = None
        RecommendEngine.instance()

    @property
    def is_ready(self) -> bool:
        return self._ready

    @property
    def load_error(self) -> Optional[str]:
        return self._load_error

    def _try_load(self) -> None:
        self._skip = bool(os.environ.get('DJANGO_SKIP_ML_LOAD'))
        if self._skip:
            logger.info('ML load skipped (DJANGO_SKIP_ML_LOAD)')
            return
        ml = settings.RECOMMENDATION_ML
        model_path = Path(ml['MODEL_PATH'])
        meta_path = Path(ml['MODEL_METADATA_PATH'])
        if not model_path.exists() or not meta_path.exists():
            self._load_error = 'Thiếu artifact BiLSTM (model/metadata). Hãy retrain.'
            logger.warning(self._load_error)
            return
        try:
            self.model = load_model(model_path)
            metadata = json.loads(meta_path.read_text(encoding='utf-8'))
            self.max_len = int(metadata['max_len'])
            self.product_classes = [int(x) for x in metadata['product_classes']]
            self.product_to_encoded = {pid: idx + 1 for idx, pid in enumerate(self.product_classes)}
            self._ready = True
            self._load_error = None
            logger.info('RecommendEngine ready with BiLSTM.')
        except Exception as exc:
            self._load_error = str(exc)
            logger.exception('BiLSTM load failed')

    def user_interacted_products(self, user_id: int) -> Set[int]:
        pids = set(
            EventLog.objects.filter(
                user_id=user_id,
                product_id__isnull=False,
                event_type__in=[
                    EventLog.EventType.PRODUCT_VIEW,
                    EventLog.EventType.PRODUCT_CLICK,
                    EventLog.EventType.ADD_TO_CART,
                    EventLog.EventType.PURCHASE,
                ],
            ).values_list('product_id', flat=True)
        )
        return {int(x) for x in pids}

    def _build_user_sequence(self, user_id: int) -> Optional[Tuple[np.ndarray, np.ndarray]]:
        rows = list(
            EventLog.objects.filter(
                user_id=user_id,
                event_type__in=list(EVENT_TO_ACTION.keys()),
                product_id__isnull=False,
            )
            .values('event_type', 'product_id')
            .order_by('-timestamp')[: self.max_len * 5]
        )
        if not rows:
            return None
        rows.reverse()
        seq_action: List[int] = []
        seq_product: List[int] = []
        for row in rows:
            pid = int(row['product_id'])
            if pid not in self.product_to_encoded:
                continue
            action_name = EVENT_TO_ACTION.get(row['event_type'])
            action_id = ACTION_ID_MAP.get(action_name or '')
            if action_id is None:
                continue
            seq_action.append(action_id)
            seq_product.append(self.product_to_encoded[pid])
        if not seq_action:
            return None
        x_action = pad_sequences([seq_action], maxlen=self.max_len, padding='pre', truncating='pre')
        x_product = pad_sequences([seq_product], maxlen=self.max_len, padding='pre', truncating='pre')
        return x_action, x_product

    def recommend(
        self,
        external_user_id: int,
        top_k: int = 10,
        exclude_products: Optional[List[int]] = None,
    ) -> tuple[List[int], str, float]:
        t0 = time.perf_counter()
        exclude: Set[int] = set(exclude_products or [])
        exclude |= self.user_interacted_products(external_user_id)

        if not self._ready or self.model is None:
            pids = cold_start_recommendations(external_user_id, top_k, exclude)
            return pids, 'cold_start_no_model', (time.perf_counter() - t0) * 1000

        user_seq = self._build_user_sequence(external_user_id)
        if user_seq is None:
            pids = cold_start_recommendations(external_user_id, top_k, exclude)
            return pids, 'cold_start_new_user', (time.perf_counter() - t0) * 1000

        x_action, x_product = user_seq
        probs = self.model.predict([x_action, x_product], verbose=0)[0]
        ranked = np.argsort(probs)[::-1]

        out: List[int] = []
        for enc_pid in ranked:
            if enc_pid == 0:
                continue
            idx = int(enc_pid) - 1
            if idx < 0 or idx >= len(self.product_classes):
                continue
            pid = int(self.product_classes[idx])
            if pid in exclude or pid in out:
                continue
            out.append(pid)
            if len(out) >= top_k:
                break

        if len(out) < top_k:
            for pid in popular_product_ids(top_k * 2):
                if pid in exclude or pid in out:
                    continue
                out.append(pid)
                if len(out) >= top_k:
                    break
        return out, 'bilstm_sequence', (time.perf_counter() - t0) * 1000
