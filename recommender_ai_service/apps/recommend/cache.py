"""Redis cache layer for the recommendation service."""
import json
import logging
from typing import List, Optional

from django.conf import settings
from django.core.cache import cache

logger = logging.getLogger(__name__)

_RECOMMEND_PREFIX = 'rec:user:'
_BESTSELLER_KEY = 'rec:bestsellers'
_TRENDING_KEY = 'rec:trending'


class RecommendCache:
    """
    Thin wrapper around Django's cache (Redis backend).
    All methods are fail-safe — cache errors never propagate to the caller.
    """

    def get_recommendations(self, user_id: int) -> Optional[List[int]]:
        """Return cached recommendation list for user_id, or None on miss/error."""
        try:
            data = cache.get(f'{_RECOMMEND_PREFIX}{user_id}')
            if data is not None:
                return json.loads(data)
        except Exception as exc:
            logger.warning('Cache GET error for user %s: %s', user_id, exc)
        return None

    def set_recommendations(self, user_id: int, product_ids: List[int]) -> None:
        """Cache recommendation list with TTL from settings."""
        ttl = settings.ML_SETTINGS['RECOMMEND_CACHE_TTL']
        try:
            cache.set(f'{_RECOMMEND_PREFIX}{user_id}', json.dumps(product_ids), timeout=ttl)
        except Exception as exc:
            logger.warning('Cache SET error for user %s: %s', user_id, exc)

    def invalidate_user(self, user_id: int) -> None:
        """Clear cached recommendations for a user (e.g. after a purchase)."""
        try:
            cache.delete(f'{_RECOMMEND_PREFIX}{user_id}')
        except Exception as exc:
            logger.warning('Cache DELETE error for user %s: %s', user_id, exc)

    def get_bestsellers(self) -> Optional[List[int]]:
        """Return cached bestseller product_ids list."""
        try:
            data = cache.get(_BESTSELLER_KEY)
            if data is not None:
                return json.loads(data)
        except Exception as exc:
            logger.warning('Cache GET bestsellers error: %s', exc)
        return None

    def set_bestsellers(self, product_ids: List[int]) -> None:
        """Cache bestseller list with TTL from settings."""
        ttl = settings.ML_SETTINGS['BESTSELLER_CACHE_TTL']
        try:
            cache.set(_BESTSELLER_KEY, json.dumps(product_ids), timeout=ttl)
            logger.info('Bestsellers cached: %s products', len(product_ids))
        except Exception as exc:
            logger.warning('Cache SET bestsellers error: %s', exc)

    def get_trending(self) -> Optional[List[int]]:
        try:
            data = cache.get(_TRENDING_KEY)
            return json.loads(data) if data else None
        except Exception:
            return None

    def set_trending(self, product_ids: List[int]) -> None:
        try:
            cache.set(_TRENDING_KEY, json.dumps(product_ids), timeout=3600)
        except Exception:
            pass
