"""
HTTP client to fetch product metadata from product_service.

Used to enrich recommendation output (name, image, price) when the API
caller requests full product objects instead of just IDs.

Design:
- Per-product results are cached in Redis for 1 hour (products change rarely)
- Timeouts are short (500ms) — recommendation latency is critical
- Failures return None silently — recommendations still work without enrichment
"""
import logging
from typing import Dict, List, Optional

import requests
from django.conf import settings
from django.core.cache import cache

logger = logging.getLogger(__name__)

_PRODUCT_CACHE_TTL = 3600  # 1 hour


def _cache_key(product_id: int) -> str:
    return f'product_meta:{product_id}'


def get_product(product_id: int) -> Optional[Dict]:
    """
    Fetch a single product's metadata.
    Returns dict with keys: id, name, slug, price, image_url, category_id, brand_id
    Returns None on error or timeout.
    """
    key = _cache_key(product_id)
    cached = cache.get(key)
    if cached is not None:
        return cached

    url = f"{settings.PRODUCT_SERVICE_URL}/api/catalog/products/{product_id}/"
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
    """
    Fetch multiple products, leveraging per-product cache.
    Returns dict mapping product_id → metadata (missing ones are omitted).
    """
    result = {}
    uncached = []

    for pid in product_ids:
        cached = cache.get(_cache_key(pid))
        if cached is not None:
            result[pid] = cached
        else:
            uncached.append(pid)

    if uncached:
        url = f"{settings.PRODUCT_SERVICE_URL}/api/catalog/products/"
        try:
            resp = requests.get(url, params={'ids': ','.join(map(str, uncached))}, timeout=1.0)
            resp.raise_for_status()
            for item in resp.json().get('results', []):
                pid = item['id']
                result[pid] = item
                cache.set(_cache_key(pid), item, timeout=_PRODUCT_CACHE_TTL)
        except Exception as exc:
            logger.debug('Bulk product fetch failed: %s', exc)

    return result
