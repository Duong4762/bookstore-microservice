"""HTTP client tới product_service để enrich kết quả gợi ý."""
import logging
from typing import Dict, List, Optional

import requests
from django.conf import settings
from django.core.cache import cache

logger = logging.getLogger(__name__)
_PRODUCT_CACHE_TTL = 3600


def _cache_key(product_id: int) -> str:
    return f'ai_rec:product_meta:{product_id}'


def get_product(product_id: int) -> Optional[Dict]:
    key = _cache_key(product_id)
    cached = cache.get(key)
    if cached is not None:
        return cached
    url = f"{settings.PRODUCT_SERVICE_URL}/api/products/{product_id}/"
    try:
        resp = requests.get(url, timeout=0.5)
        resp.raise_for_status()
        data = resp.json()
        cache.set(key, data, timeout=_PRODUCT_CACHE_TTL)
        return data
    except Exception as exc:
        logger.debug('Failed to fetch product %s: %s', product_id, exc)
        return None


def get_products_bulk(product_ids: List[int]) -> Dict[int, Dict]:
    result = {}
    uncached = []
    for pid in product_ids:
        cached = cache.get(_cache_key(pid))
        if cached is not None:
            result[pid] = cached
        else:
            uncached.append(pid)
    if uncached:
        for pid in uncached:
            one = get_product(pid)
            if one:
                result[pid] = one
    return result


def list_products(
    *,
    search: str = '',
    category_id: Optional[int] = None,
    brand_id: Optional[int] = None,
    in_stock: Optional[bool] = None,
    limit: int = 50,
) -> List[Dict]:
    """Query product list endpoint for RAG retrieval."""
    params: Dict[str, str] = {}
    if search.strip():
        params['search'] = search.strip()[:200]
    if category_id:
        params['category_id'] = str(category_id)
    if brand_id:
        params['brand_id'] = str(brand_id)
    if in_stock is True:
        params['in_stock'] = 'true'
    url = f"{settings.PRODUCT_SERVICE_URL}/api/products/"
    try:
        resp = requests.get(url, params=params, timeout=1.5)
        resp.raise_for_status()
        body = resp.json()
        rows = body.get('results', body) if isinstance(body, dict) else body
        if not isinstance(rows, list):
            return []
        return rows[: max(1, min(limit, 200))]
    except Exception as exc:
        logger.debug('Failed to list products via catalog proxy: %s', exc)
        return []


