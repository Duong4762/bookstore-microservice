"""Cache embedding user (Redis / Django cache) — giảm độ trễ inference."""
from __future__ import annotations

import logging
from typing import Optional

import numpy as np
from django.conf import settings
from django.core.cache import cache

logger = logging.getLogger(__name__)


class UserEmbeddingCache:
    """Vector float32 serialized qua bytes numpy."""

    @staticmethod
    def _key(user_id: int) -> str:
        prefix = settings.RECOMMENDATION_ML.get('CACHE_KEY_PREFIX', 'bilstm_rec:user:')
        return f'{prefix}{user_id}'

    @classmethod
    def get(cls, user_id: int) -> Optional[np.ndarray]:
        try:
            raw = cache.get(cls._key(user_id))
            if raw is None:
                return None
            return np.frombuffer(raw, dtype=np.float32)
        except Exception as exc:
            logger.debug('user emb cache miss/read error: %s', exc)
            return None

    @classmethod
    def set(cls, user_id: int, vec: np.ndarray) -> None:
        try:
            ttl = int(settings.RECOMMENDATION_ML['USER_EMB_CACHE_TTL'])
            cache.set(cls._key(user_id), vec.astype(np.float32).tobytes(), timeout=ttl)
        except Exception as exc:
            logger.debug('user emb cache set failed: %s', exc)

    @classmethod
    def invalidate(cls, user_id: int) -> None:
        try:
            cache.delete(cls._key(user_id))
        except Exception as exc:
            logger.debug('user emb cache invalidate failed: %s', exc)
