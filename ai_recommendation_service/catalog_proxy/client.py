"""HTTP client tới product_service để enrich kết quả gợi ý."""
import logging
from typing import Any, Dict, List, Optional

import requests
from django.conf import settings
from django.core.cache import cache

logger = logging.getLogger(__name__)
_PRODUCT_CACHE_TTL = 3600


def _cache_key(product_id: int) -> str:
    return f'gnn_rec:product_meta:{product_id}'


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


def search_products(query: str, *, limit: int = 8) -> List[Dict[str, Any]]:
    """GET /api/products/?search= — hỗ trợ RAG khi người dùng hỏi theo tên ngoài tập gợi ý đồ thị."""
    q = (query or '').strip()
    if len(q) < 2:
        return []
    url = f"{settings.PRODUCT_SERVICE_URL}/api/products/"
    try:
        resp = requests.get(url, params={'search': q}, timeout=2.0)
        resp.raise_for_status()
        data = resp.json()
        rows = data.get('results', data) if isinstance(data, dict) else data
        if not isinstance(rows, list):
            return []
        return rows[:limit]
    except Exception as exc:
        logger.debug('search_products failed: %s', exc)
        return []


def list_products(*, limit: int = 200, search: str = '') -> List[Dict[str, Any]]:
    """Lấy danh sách sản phẩm từ product_service (gom nhiều trang)."""
    out: List[Dict[str, Any]] = []
    page = 1
    q = (search or '').strip()
    base_params: Dict[str, Any] = {}
    if q:
        base_params['search'] = q
    url = f"{settings.PRODUCT_SERVICE_URL}/api/products/"
    while len(out) < limit and page <= 50:
        params = dict(base_params)
        params['page'] = page
        try:
            resp = requests.get(url, params=params, timeout=2.5)
            resp.raise_for_status()
            data = resp.json()
        except Exception as exc:
            logger.debug('list_products failed at page %s: %s', page, exc)
            break
        rows = data.get('results', data) if isinstance(data, dict) else data
        if not isinstance(rows, list) or not rows:
            break
        out.extend(rows)
        if len(out) >= limit:
            break
        has_next = bool(data.get('next')) if isinstance(data, dict) else False
        if not has_next:
            break
        page += 1
    return out[:limit]
