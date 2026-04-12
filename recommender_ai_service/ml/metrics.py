"""
Ranking metrics for next-product recommendation.

Metrics implemented:
- Recall@K       — fraction of correct items in top-K
- HitRate@K      — 1 if target in top-K else 0, averaged
- MRR@K          — mean reciprocal rank (how high the target appears)
- NDCG@K         — normalised discounted cumulative gain

All functions accept:
    preds  (np.ndarray or list): shape (N, K) — top-K predicted indices per sample
    targets (np.ndarray or list): shape (N,)  — true target index per sample
"""
import numpy as np


def recall_at_k(preds: np.ndarray, targets: np.ndarray, k: int) -> float:
    """
    Recall@K: fraction of samples where the ground-truth item appears
    in the top-K predictions.  In next-item prediction this is identical
    to HitRate@K because there is exactly one relevant item per sample.
    """
    preds = np.array(preds)[:, :k]
    targets = np.array(targets)
    hits = (preds == targets[:, None]).any(axis=1)
    return float(hits.mean())


def hit_rate_at_k(preds: np.ndarray, targets: np.ndarray, k: int) -> float:
    """Alias for recall_at_k (same semantics in single-target setting)."""
    return recall_at_k(preds, targets, k)


def mrr_at_k(preds: np.ndarray, targets: np.ndarray, k: int) -> float:
    """
    MRR@K: for each sample, if the target appears in top-K at rank r (1-indexed),
    its contribution is 1/r; if not in top-K, contribution is 0.
    """
    preds = np.array(preds)[:, :k]
    targets = np.array(targets)
    rrs = []
    for pred_row, target in zip(preds, targets):
        positions = np.where(pred_row == target)[0]
        rrs.append(1.0 / (positions[0] + 1) if len(positions) > 0 else 0.0)
    return float(np.mean(rrs))


def ndcg_at_k(preds: np.ndarray, targets: np.ndarray, k: int) -> float:
    """
    NDCG@K: normalised discounted cumulative gain.
    Ideal DCG = 1 (target at rank 1), so NDCG = 1/log2(rank+1) when hit, else 0.
    """
    preds = np.array(preds)[:, :k]
    targets = np.array(targets)
    ndcgs = []
    for pred_row, target in zip(preds, targets):
        positions = np.where(pred_row == target)[0]
        if len(positions) > 0:
            rank = positions[0] + 1  # 1-indexed
            ndcgs.append(1.0 / np.log2(rank + 1))
        else:
            ndcgs.append(0.0)
    return float(np.mean(ndcgs))


def compute_all_metrics(preds: np.ndarray, targets: np.ndarray) -> dict:
    """
    Compute all ranking metrics for k in {5, 10}.
    Returns dict suitable for logging / checkpoint metadata.
    """
    return {
        'recall@5': recall_at_k(preds, targets, 5),
        'recall@10': recall_at_k(preds, targets, 10),
        'hit_rate@5': hit_rate_at_k(preds, targets, 5),
        'hit_rate@10': hit_rate_at_k(preds, targets, 10),
        'mrr@5': mrr_at_k(preds, targets, 5),
        'mrr@10': mrr_at_k(preds, targets, 10),
        'ndcg@5': ndcg_at_k(preds, targets, 5),
        'ndcg@10': ndcg_at_k(preds, targets, 10),
    }
