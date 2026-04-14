"""
Serving layer: tải GNN + HeteroData + FAISS một lần; GET recommend → embedding user → top-K.

Monitoring: gọi hook tùy chọn RECOMMENDATION_ML['MONITORING_HOOK'] nếu là callable.
"""
from __future__ import annotations

import logging
import os
import threading
import time
from pathlib import Path
from typing import TYPE_CHECKING, Any, Dict, List, Optional, Set

import numpy as np
import torch
from django.conf import settings

from .cold_start import cold_start_recommendations, popular_product_ids
from .embedding_cache import UserEmbeddingCache
from .faiss_index import ProductFaissIndex

if TYPE_CHECKING:
    from torch_geometric.data import HeteroData
    from .gnn_model import HeteroGraphSAGEModel

logger = logging.getLogger(__name__)


def _monitor(event: str, payload: Dict[str, Any]) -> None:
    hook = settings.RECOMMENDATION_ML.get('MONITORING_HOOK')
    if callable(hook):
        try:
            hook(event, payload)
        except Exception as exc:
            logger.debug('monitoring hook error: %s', exc)


class RecommendEngine:
    """Singleton — model + graph + FAISS giữ trong RAM."""

    _instance: Optional['RecommendEngine'] = None
    _lock = threading.RLock()

    def __init__(self) -> None:
        self._ready = False
        self._skip = False
        self.model: Optional[Any] = None
        self.data: Optional[Any] = None
        self.mappings: Optional[Dict[str, Any]] = None
        self.faiss_index = ProductFaissIndex()
        self.device = torch.device('cpu')
        self._load_error: Optional[str] = None

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

    def _try_load(self) -> None:
        self._skip = bool(os.environ.get('DJANGO_SKIP_ML_LOAD'))
        if self._skip:
            logger.info('ML load skipped (DJANGO_SKIP_ML_LOAD)')
            return
        ml = settings.RECOMMENDATION_ML
        self.device = torch.device(
            'cuda' if torch.cuda.is_available() and ml.get('USE_CUDA') else 'cpu'
        )
        bundle_path = Path(ml['HETERODATA_PATH'])
        ckpt_path = Path(ml['MODEL_PATH'])
        faiss_dir = Path(ml['FAISS_DIR'])
        try:
            try:
                from .gnn_model import HeteroGraphSAGEModel
                from .graph_preprocess import load_heterodata_bundle
            except Exception as exc:
                self._load_error = f'Thiếu dependency ML runtime: {exc}'
                logger.warning(self._load_error)
                return
            if not bundle_path.exists() or not ckpt_path.exists() or not (faiss_dir / 'faiss.index').exists():
                self._load_error = 'Thiếu artifact (heterodata / model / faiss). Chạy train hoặc POST /api/recommend/retrain/'
                logger.warning(self._load_error)
                return
            self.data, self.mappings = load_heterodata_bundle(bundle_path)
            try:
                ckpt = torch.load(ckpt_path, map_location=self.device, weights_only=False)
            except TypeError:
                ckpt = torch.load(ckpt_path, map_location=self.device)
            self.model = HeteroGraphSAGEModel(
                int(ckpt['hidden_dim']),
                int(ckpt['out_dim']),
                ckpt['num_nodes_dict'],
            )
            self.model.load_state_dict(ckpt['model_state'])
            self.model.to(self.device)
            self.model.eval()
            self.faiss_index.load(faiss_dir)
            self._ready = True
            self._load_error = None
            logger.info('RecommendEngine ready (device=%s)', self.device)
            _monitor('ml_load_ok', {'device': str(self.device)})
        except Exception as exc:
            self._load_error = str(exc)
            logger.error('RecommendEngine load failed: %s', exc, exc_info=True)
            _monitor('ml_load_error', {'error': str(exc)})

    @property
    def is_ready(self) -> bool:
        return self._ready

    @property
    def load_error(self) -> Optional[str]:
        return self._load_error

    def user_interacted_products(self, external_user_id: int) -> Set[int]:
        """Loại sản phẩm user đã tương tác mạnh (add_to_cart / purchase)."""
        from tracking.models import EventLog

        pids = set(
            EventLog.objects.filter(
                user_id=external_user_id,
                product_id__isnull=False,
                event_type__in=[
                    EventLog.EventType.ADD_TO_CART,
                    EventLog.EventType.PURCHASE,
                ],
            ).values_list('product_id', flat=True)
        )
        return pids

    def _user_embedding(self, external_user_id: int) -> Optional[np.ndarray]:
        assert self.model is not None and self.data is not None and self.mappings is not None
        user_stoi: Dict[int, int] = self.mappings['user_stoi']
        if external_user_id not in user_stoi:
            return None
        cached = UserEmbeddingCache.get(external_user_id)
        if cached is not None:
            return cached
        ui = user_stoi[external_user_id]
        from .graph_preprocess import edge_weight_dict_from_data

        d = self.data.clone().to(self.device)
        ew = {k: v.to(self.device) for k, v in edge_weight_dict_from_data(d).items()}
        with torch.no_grad():
            u_all, _ = self.model.user_product_embeddings(d, ew)
            vec = u_all[ui].cpu().numpy()
        UserEmbeddingCache.set(external_user_id, vec)
        return vec

    def recommend(
        self,
        external_user_id: int,
        top_k: int = 10,
        exclude_products: Optional[List[int]] = None,
    ) -> tuple[List[int], str, float]:
        """
        Trả về (product_ids, source, latency_ms).
        source: gnn_faiss | cold_start | cold_start_no_graph
        """
        t0 = time.perf_counter()
        exclude: Set[int] = set(exclude_products or [])
        exclude |= self.user_interacted_products(external_user_id)

        if not self._ready:
            pids = cold_start_recommendations(external_user_id, top_k, exclude)
            dt = (time.perf_counter() - t0) * 1000
            _monitor('recommend', {'source': 'cold_start_no_ml', 'user_id': external_user_id, 'latency_ms': dt})
            return pids, 'cold_start_no_ml', dt

        assert self.mappings is not None
        vec = self._user_embedding(external_user_id)
        if vec is None:
            pids = cold_start_recommendations(external_user_id, top_k, exclude)
            dt = (time.perf_counter() - t0) * 1000
            _monitor('recommend', {'source': 'cold_start_new_user', 'user_id': external_user_id})
            return pids, 'cold_start_new_user', dt

        rows, _ = self.faiss_index.search(vec, top_k + len(exclude) + 10)
        out: List[int] = []
        for pid in rows:
            if pid in exclude:
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
        # Fallback cuối: nếu vẫn rỗng do exclude quá chặt, trả bestseller không lọc.
        if not out:
            for pid in popular_product_ids(top_k):
                if pid in out:
                    continue
                out.append(pid)
                if len(out) >= top_k:
                    break
        dt = (time.perf_counter() - t0) * 1000
        _monitor('recommend', {'source': 'gnn_faiss', 'user_id': external_user_id, 'latency_ms': dt})
        return out, 'gnn_faiss', dt
