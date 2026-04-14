"""FAISS index trên embedding sản phẩm (inner product / cosine trên vector đã chuẩn hoá)."""
from __future__ import annotations

import logging
from pathlib import Path
from typing import List, Optional, Tuple

import numpy as np

logger = logging.getLogger(__name__)

try:
    import faiss
except ImportError:
    faiss = None  # type: ignore


class ProductFaissIndex:
    """Singleton-friendly: load numpy + faiss index; map hàng → product_id gốc."""

    def __init__(self) -> None:
        self._index = None
        self._product_ids: Optional[np.ndarray] = None
        self._dim: int = 0

    def build(self, product_embeddings: np.ndarray, product_ids: List[int]) -> None:
        if faiss is None:
            raise RuntimeError('faiss-cpu chưa được cài đặt')
        if len(product_ids) != len(product_embeddings):
            raise ValueError('product_ids length must match embedding rows')
        self._dim = product_embeddings.shape[1]
        self._product_ids = np.array(product_ids, dtype=np.int64)
        x = product_embeddings.astype('float32')
        faiss.normalize_L2(x)
        self._index = faiss.IndexFlatIP(self._dim)
        self._index.add(x)
        logger.info('FAISS IndexFlatIP: %d vectors, dim=%d', x.shape[0], self._dim)

    def search(self, query_vec: np.ndarray, k: int) -> Tuple[List[int], List[float]]:
        if self._index is None or self._product_ids is None:
            return [], []
        q = query_vec.astype('float32').reshape(1, -1)
        faiss.normalize_L2(q)
        scores, idx = self._index.search(q, min(k, self._index.ntotal))
        idx = idx[0]
        scores = scores[0]
        pids = []
        sims = []
        for i, s in zip(idx, scores):
            if i < 0:
                continue
            pids.append(int(self._product_ids[i]))
            sims.append(float(s))
        return pids, sims

    def save(self, dir_path: Path) -> None:
        dir_path.mkdir(parents=True, exist_ok=True)
        if faiss is None or self._index is None or self._product_ids is None:
            return
        faiss.write_index(self._index, str(dir_path / 'faiss.index'))
        np.save(dir_path / 'product_ids.npy', self._product_ids)
        np.save(dir_path / 'dim.npy', np.array([self._dim]))

    def load(self, dir_path: Path) -> None:
        if faiss is None:
            raise RuntimeError('faiss-cpu chưa được cài đặt')
        idx_path = dir_path / 'faiss.index'
        if not idx_path.exists():
            raise FileNotFoundError(idx_path)
        self._index = faiss.read_index(str(idx_path))
        self._product_ids = np.load(dir_path / 'product_ids.npy')
        self._dim = int(np.load(dir_path / 'dim.npy')[0])
        logger.info('FAISS loaded: ntotal=%d', self._index.ntotal)
