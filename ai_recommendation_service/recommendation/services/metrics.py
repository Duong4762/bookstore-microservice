"""Đánh giá ranking: Recall@K, Precision@K."""
from __future__ import annotations

from typing import Iterable, List, Set


def recall_at_k(recommended: List[int], relevant: Set[int], k: int) -> float:
    if not relevant:
        return 0.0
    top = set(recommended[:k])
    return len(top & relevant) / len(relevant)


def precision_at_k(recommended: List[int], relevant: Set[int], k: int) -> float:
    if k <= 0:
        return 0.0
    top = set(recommended[:k])
    return len(top & relevant) / k


def mean_metric_per_user(
    user_to_recommended: dict,
    user_to_relevant: dict,
    k: int,
    metric_fn,
) -> float:
    vals = []
    for uid, rec in user_to_recommended.items():
        rel = user_to_relevant.get(uid, set())
        if not rel:
            continue
        vals.append(metric_fn(rec, rel, k))
    return sum(vals) / len(vals) if vals else 0.0
