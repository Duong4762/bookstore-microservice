"""
Recommendation business logic — orchestrates ML inference, caching, and cold start.

Flow:
  1. Redis cache hit  →  return immediately
  2. ML model ready   →  run LSTM inference
  3. Fallback          →  bestsellers / trending
"""
import logging
from datetime import timedelta
from typing import List, Optional

from django.conf import settings
from django.db.models import Count
from django.utils import timezone

from .cache import RecommendCache

logger = logging.getLogger(__name__)


class RecommendationService:
    """
    Stateless service — instantiate per-request or inject as singleton.
    All external I/O is fail-safe (never raises to caller).
    """

    def __init__(self):
        self.cache = RecommendCache()

    # ── Public API ─────────────────────────────────────────────────────────────

    def get_recommendations(
        self,
        user_id: int,
        recent_events: Optional[List[dict]] = None,
        top_k: Optional[int] = None,
        exclude_products: Optional[List[int]] = None,
    ) -> List[int]:
        """
        Main entry point.

        Args:
            user_id:        The user to recommend for.
            recent_events:  Pre-fetched events; if None, fetched from DB.
            top_k:          Number of recommendations (default from settings).
            exclude_products: Product IDs to exclude (e.g. already in cart).

        Returns:
            List of recommended product_ids, length <= top_k.
        """
        top_k = top_k or settings.ML_SETTINGS['TOP_K']

        # ── 1. Cache hit ───────────────────────────────────────────────────
        cached = self.cache.get_recommendations(user_id)
        if cached is not None:
            logger.debug('Cache hit for user=%s', user_id)
            return self._apply_exclusions(cached, exclude_products, top_k)

        # ── 2. Fetch events from DB if caller didn't supply them ───────────
        if recent_events is None:
            recent_events = self._fetch_user_events(user_id)

        # ── 3. Cold start — no user history ───────────────────────────────
        if not recent_events:
            logger.info('Cold start for user=%s (no history)', user_id)
            result = self._cold_start(top_k)
            self.cache.set_recommendations(user_id, result)
            return self._apply_exclusions(result, exclude_products, top_k)

        # ── 4. ML inference ────────────────────────────────────────────────
        ml_result = self._ml_predict(recent_events, top_k)
        if ml_result:
            self.cache.set_recommendations(user_id, ml_result)
            return self._apply_exclusions(ml_result, exclude_products, top_k)

        # ── 5. Graceful fallback ───────────────────────────────────────────
        logger.warning('ML unavailable for user=%s, using bestsellers', user_id)
        result = self._cold_start(top_k)
        self.cache.set_recommendations(user_id, result)
        return self._apply_exclusions(result, exclude_products, top_k)

    def invalidate_user_cache(self, user_id: int) -> None:
        """Call after a purchase to force fresh recommendations."""
        self.cache.invalidate_user(user_id)

    # ── Private helpers ────────────────────────────────────────────────────────

    def _fetch_user_events(self, user_id: int) -> List[dict]:
        """Fetch user's most recent events from DB (up to SEQUENCE_LENGTH)."""
        from apps.tracking.models import EventLog
        seq_len = settings.ML_SETTINGS['SEQUENCE_LENGTH']
        events = (
            EventLog.objects
            .filter(user_id=user_id, product_id__isnull=False)
            .order_by('-timestamp')[:seq_len]
        )
        return [
            {
                'event_type': e.event_type,
                'product_id': e.product_id,
                'category_id': e.category_id,
                'brand_id': e.brand_id,
            }
            for e in reversed(list(events))
        ]

    def _ml_predict(self, events: List[dict], top_k: int) -> List[int]:
        """Run LSTM model inference; returns [] on any error."""
        try:
            from ml.inference import ModelLoader
            loader = ModelLoader.instance()
            if not loader.is_ready:
                return []
            return loader.predict(events, top_k=top_k)
        except Exception as exc:
            logger.error('ML inference error: %s', exc, exc_info=True)
            return []

    def _cold_start(self, top_k: int) -> List[int]:
        """
        Returns bestselling products for new users or when model fails.
        Priority: Redis cache → DB computation → []
        """
        bestsellers = self.cache.get_bestsellers()
        if bestsellers:
            return bestsellers[:top_k]

        bestsellers = self._compute_bestsellers()
        if bestsellers:
            self.cache.set_bestsellers(bestsellers)
            return bestsellers[:top_k]

        return []

    def _compute_bestsellers(self) -> List[int]:
        """Query last N days of purchase events ranked by count."""
        from apps.tracking.models import EventLog
        days = settings.ML_SETTINGS['COLD_START_DAYS']
        count = settings.ML_SETTINGS['BESTSELLER_COUNT']
        since = timezone.now() - timedelta(days=days)

        rows = (
            EventLog.objects
            .filter(event_type='purchase', timestamp__gte=since, product_id__isnull=False)
            .values('product_id')
            .annotate(cnt=Count('id'))
            .order_by('-cnt')[:count]
        )
        result = [row['product_id'] for row in rows]
        logger.info('Computed %d bestsellers from last %d days', len(result), days)
        return result

    @staticmethod
    def _apply_exclusions(
        product_ids: List[int],
        exclude: Optional[List[int]],
        top_k: int,
    ) -> List[int]:
        if not exclude:
            return product_ids[:top_k]
        exclude_set = set(exclude)
        filtered = [p for p in product_ids if p not in exclude_set]
        return filtered[:top_k]
