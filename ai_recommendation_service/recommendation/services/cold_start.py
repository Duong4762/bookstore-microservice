"""
Fallback khi user lạnh / model chưa sẵn sàng:
- Sản phẩm phổ biến (theo purchase / cart / click)
- Gợi ý theo category_id gần nhất của user
- Gợi ý theo query tìm kiếm gần nhất (sản phẩm từng xuất hiện cùng session có search)
"""
from __future__ import annotations

from typing import List, Set

from django.db.models import Count

from tracking.models import EventLog


def popular_product_ids(limit: int = 20) -> List[int]:
    qs = (
        EventLog.objects.filter(
            event_type__in=[
                EventLog.EventType.PURCHASE,
                EventLog.EventType.ADD_TO_CART,
                EventLog.EventType.PRODUCT_CLICK,
            ],
            product_id__isnull=False,
        )
        .values('product_id')
        .annotate(c=Count('id'))
        .order_by('-c')[: limit * 2]
    )
    out: List[int] = []
    seen: Set[int] = set()
    for row in qs:
        pid = row['product_id']
        if pid in seen:
            continue
        seen.add(pid)
        out.append(pid)
        if len(out) >= limit:
            break
    return out


def _last_category_id(user_id: int) -> int | None:
    ev = (
        EventLog.objects.filter(user_id=user_id, category_id__isnull=False)
        .order_by('-timestamp')
        .first()
    )
    return ev.category_id if ev else None


def category_based_product_ids(user_id: int, limit: int) -> List[int]:
    cid = _last_category_id(user_id)
    if cid is None:
        return []
    pids = list(
        EventLog.objects.filter(category_id=cid, product_id__isnull=False)
        .values_list('product_id', flat=True)
        .distinct()[: limit * 2]
    )
    return list(dict.fromkeys(pids))[:limit]


def _last_search_session(user_id: int) -> tuple[str | None, str | None]:
    ev = (
        EventLog.objects.filter(user_id=user_id, event_type=EventLog.EventType.SEARCH)
        .exclude(keyword='')
        .order_by('-timestamp')
        .first()
    )
    if not ev:
        return None, None
    return ev.session_id, ev.keyword.strip().lower()[:200]


def query_anchored_product_ids(user_id: int, limit: int) -> List[int]:
    session_id, kw = _last_search_session(user_id)
    if not session_id or not kw:
        return []
    pids = list(
        EventLog.objects.filter(session_id=session_id, product_id__isnull=False)
        .exclude(event_type=EventLog.EventType.SEARCH)
        .values_list('product_id', flat=True)
        .distinct()[: limit * 2]
    )
    return list(dict.fromkeys(pids))[:limit]


def cold_start_recommendations(user_id: int, top_k: int, exclude: Set[int]) -> List[int]:
    """Kết hợp popular + category + query; loại exclude."""
    buckets: List[List[int]] = [
        category_based_product_ids(user_id, top_k),
        query_anchored_product_ids(user_id, top_k),
        popular_product_ids(top_k * 2),
    ]
    out: List[int] = []
    seen: Set[int] = set(exclude)
    for bucket in buckets:
        for pid in bucket:
            if pid in seen:
                continue
            seen.add(pid)
            out.append(pid)
            if len(out) >= top_k:
                return out
    return out
