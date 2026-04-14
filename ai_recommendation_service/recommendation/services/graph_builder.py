"""
Xây dựng knowledge graph dị thể từ EventLog và quan hệ sản phẩm.

Cạnh:
  - user → product: tương tác (view/click/add_to_cart/purchase), trọng số tổng hợp
  - user → query: tìm kiếm
  - product → category: belongs_to
  - product ↔ product: đồng click (co-click), cạnh hai chiều

Trọng số user–product:
  w(u,p) = α·clicks + β·add_to_cart + γ·purchases + η·views
  (η cấu hình qua VIEW_WEIGHT_SCALE trong settings)

Hỗ trợ cập nhật gia tăng sau mỗi event (apply_event).
"""
from __future__ import annotations

import logging
from collections import defaultdict
from typing import DefaultDict, Dict, List, Optional, Set, Tuple

from django.conf import settings
from tracking.models import EventLog

from .graph_storage import GraphStorage, NodeKey, NodeType

logger = logging.getLogger(__name__)


def _norm_keyword(kw: str) -> str:
    s = (kw or '').strip().lower()[:200]
    return s or '__empty__'


class GraphBuilder:
    """Dựng / cập nhật đồ thị trên lớp GraphStorage."""

    def __init__(self, storage: GraphStorage) -> None:
        self.storage = storage

    def _weights(self) -> Tuple[float, float, float, float]:
        ml = settings.RECOMMENDATION_ML
        return (
            float(ml['ALPHA_CLICK']),
            float(ml['BETA_CART']),
            float(ml['GAMMA_PURCHASE']),
            float(ml['ETA_VIEW']),
        )

    def _co_click_min(self) -> int:
        return int(settings.RECOMMENDATION_ML['CO_CLICK_MIN_COUNT'])

    def build_from_database(self, full_rebuild: bool = True) -> None:
        """
        Quét toàn bộ EventLog, dựng lại đồ thị.
        Co-click chỉ cập nhật đầy đủ khi gọi hàm này (full scan).
        """
        if full_rebuild:
            self.storage.clear()

        alpha, beta, gamma, eta = self._weights()

        # Đếm theo (user, product) theo loại event
        up_counts: DefaultDict[Tuple[int, int], DefaultDict[str, int]] = defaultdict(
            lambda: defaultdict(int)
        )
        # product → category (ưu tiên bản ghi có category_id)
        product_category: Dict[int, int] = {}
        # user → query
        uq_counts: DefaultDict[Tuple[int, str], int] = defaultdict(int)
        # session → ordered products for co-click (click + view)
        session_products: DefaultDict[str, List[int]] = defaultdict(list)

        qs = EventLog.objects.all().only(
            'user_id', 'product_id', 'category_id', 'event_type', 'session_id', 'keyword',
        ).iterator(chunk_size=5000)

        for ev in qs:
            uid = ev.user_id
            if ev.event_type == EventLog.EventType.SEARCH:
                qk = _norm_keyword(ev.keyword)
                uq_counts[(uid, qk)] += 1
                continue

            pid = ev.product_id
            if pid is None:
                continue

            if ev.category_id:
                product_category[pid] = ev.category_id

            et = ev.event_type
            if et == EventLog.EventType.PRODUCT_VIEW:
                up_counts[(uid, pid)]['view'] += 1
                session_products[ev.session_id].append(pid)
            elif et == EventLog.EventType.PRODUCT_CLICK:
                up_counts[(uid, pid)]['click'] += 1
                session_products[ev.session_id].append(pid)
            elif et == EventLog.EventType.ADD_TO_CART:
                up_counts[(uid, pid)]['cart'] += 1
            elif et == EventLog.EventType.PURCHASE:
                up_counts[(uid, pid)]['purchase'] += 1

        # User — Product weighted edges
        for (uid, pid), counts in up_counts.items():
            w = (
                alpha * counts['click']
                + beta * counts['cart']
                + gamma * counts['purchase']
                + eta * counts['view']
            )
            if w <= 0:
                continue
            u_node: NodeKey = (NodeType.USER, uid)
            p_node: NodeKey = (NodeType.PRODUCT, pid)
            self.storage.add_edge(u_node, p_node, 'interacts', weight=w, accumulate=False)

        # User — Query
        for (uid, qk), c in uq_counts.items():
            if c <= 0:
                continue
            self.storage.add_edge(
                (NodeType.USER, uid), (NodeType.QUERY, qk), 'searches', weight=float(c), accumulate=False
            )

        # Product — Category
        for pid, cid in product_category.items():
            self.storage.add_edge(
                (NodeType.PRODUCT, pid), (NodeType.CATEGORY, cid), 'in_category', weight=1.0, accumulate=False
            )

        # Co-click: pairs within same session
        pair_counts: DefaultDict[Tuple[int, int], int] = defaultdict(int)
        for plist in session_products.values():
            seen: Set[Tuple[int, int]] = set()
            uniq = list(dict.fromkeys(plist))  # preserve order, dedupe
            for i in range(len(uniq)):
                for j in range(i + 1, len(uniq)):
                    a, b = uniq[i], uniq[j]
                    if a > b:
                        a, b = b, a
                    if (a, b) in seen:
                        continue
                    seen.add((a, b))
                    pair_counts[(a, b)] += 1

        m = self._co_click_min()
        for (a, b), cnt in pair_counts.items():
            if cnt < m:
                continue
            w = float(cnt)
            pa: NodeKey = (NodeType.PRODUCT, a)
            pb: NodeKey = (NodeType.PRODUCT, b)
            self.storage.add_edge(pa, pb, 'co_click', weight=w, accumulate=False)
            self.storage.add_edge(pb, pa, 'co_click', weight=w, accumulate=False)

        logger.info(
            'Graph build complete: %d user-product pairs, %d user-queries, %d product-cat, %d co-click pairs',
            len(up_counts),
            len(uq_counts),
            len(product_category),
            sum(1 for _ in pair_counts.values() if _ >= m),
        )

    def apply_event(self, event: EventLog) -> None:
        """
        Cập nhật gia tăng sau một event mới.
        Không tính lại co-click (cần build_from_database định kỳ).
        """
        alpha, beta, gamma, eta = self._weights()
        uid = event.user_id

        if event.event_type == EventLog.EventType.SEARCH:
            qk = _norm_keyword(event.keyword)
            self.storage.add_edge(
                (NodeType.USER, uid), (NodeType.QUERY, qk), 'searches', weight=1.0, accumulate=True
            )
            return

        pid = event.product_id
        if pid is None:
            return

        delta = 0.0
        et = event.event_type
        if et == EventLog.EventType.PRODUCT_VIEW:
            delta = eta
        elif et == EventLog.EventType.PRODUCT_CLICK:
            delta = alpha
        elif et == EventLog.EventType.ADD_TO_CART:
            delta = beta
        elif et == EventLog.EventType.PURCHASE:
            delta = gamma

        if delta <= 0:
            return

        u_node: NodeKey = (NodeType.USER, uid)
        p_node: NodeKey = (NodeType.PRODUCT, pid)
        self.storage.add_edge(u_node, p_node, 'interacts', weight=delta, accumulate=True)

        if event.category_id:
            self.storage.add_edge(
                p_node,
                (NodeType.CATEGORY, event.category_id),
                'in_category',
                weight=1.0,
                accumulate=True,
            )

    def save(self, path: Optional[str] = None) -> None:
        p = path or str(settings.RECOMMENDATION_ML['GRAPH_PICKLE_PATH'])
        from pathlib import Path
        self.storage.save(Path(p))

    def load(self, path: Optional[str] = None) -> None:
        from pathlib import Path
        p = Path(path or str(settings.RECOMMENDATION_ML['GRAPH_PICKLE_PATH']))
        if p.exists():
            self.storage.load(p)
            logger.info('Graph loaded from %s', p)
