"""
Huấn luyện GNN với BPR (pairwise ranking) trên bộ ba (user, pos_product, neg_product).

Đánh giá: tách một phần cạnh user–product làm test, tính Recall@K / Precision@K
bằng nearest neighbor trên embedding sản phẩm (giống serving).
"""
from __future__ import annotations

import logging
import random
from pathlib import Path
from typing import Any, Dict, List, Set

import numpy as np
import torch
import torch.nn.functional as F
from torch_geometric.data import HeteroData

from django.conf import settings

from .faiss_index import ProductFaissIndex
from .gnn_model import HeteroGraphSAGEModel
from .graph_preprocess import (
    EDGE_SPECS,
    edge_weight_dict_from_data,
    load_heterodata_bundle,
    save_heterodata,
    storage_to_heterodata,
)
from .graph_builder import GraphBuilder
from .graph_storage import NetworkXGraphStorage
from .metrics import precision_at_k, recall_at_k

logger = logging.getLogger(__name__)


def _num_nodes_dict(data: HeteroData) -> Dict[str, int]:
    return {nt: data[nt].num_nodes for nt in ('user', 'product', 'category', 'query')}


def _interaction_pairs(data: HeteroData) -> List[Tuple[int, int]]:
    ei = data['user', 'interacts', 'product'].edge_index
    if ei.numel() == 0:
        return []
    return list(zip(ei[0].tolist(), ei[1].tolist()))


def _train_val_split(
    pairs: List[Tuple[int, int]],
    val_ratio: float,
    seed: int,
) -> Tuple[List[Tuple[int, int]], List[Tuple[int, int]]]:
    rng = random.Random(seed)
    shuffled = pairs[:]
    rng.shuffle(shuffled)
    n_val = max(1, int(len(shuffled) * val_ratio)) if len(shuffled) > 2 else 1
    if len(shuffled) <= n_val:
        return shuffled, []
    return shuffled[n_val:], shuffled[:n_val]


def train_gnn(
    data: HeteroData,
    mappings: Dict[str, Any],
    epochs: int,
    lr: float,
    device: torch.device,
    val_ratio: float = 0.1,
    seed: int = 42,
) -> Tuple[HeteroGraphSAGEModel, Dict[str, float]]:
    ml = settings.RECOMMENDATION_ML
    hidden = int(ml['GNN_HIDDEN_DIM'])
    out_dim = int(ml['GNN_OUT_DIM'])
    neg_ratio = int(ml['BPR_NUM_NEGATIVES'])

    pairs = _interaction_pairs(data)
    if len(pairs) < 4:
        raise RuntimeError('Không đủ cạnh user–product để huấn luyện (cần ít nhất vài tương tác).')

    train_pairs, val_pairs = _train_val_split(pairs, val_ratio, seed)
    product_stoi: Dict[int, int] = mappings['product_stoi']
    num_products = data['product'].num_nodes
    all_products = list(range(num_products))

    # user -> positive product indices (train only)
    user_pos: Dict[int, Set[int]] = {}
    for u, p in train_pairs:
        user_pos.setdefault(u, set()).add(p)

    model = HeteroGraphSAGEModel(hidden, out_dim, _num_nodes_dict(data)).to(device)
    opt = torch.optim.Adam(model.parameters(), lr=lr)

    data = data.to(device)
    ew = {k: v.to(device) for k, v in edge_weight_dict_from_data(data).items()}

    def forward_emb():
        out = model.forward(data, edge_weight_dict=ew)
        u = F.normalize(out['user'], dim=-1)
        p = F.normalize(out['product'], dim=-1)
        return u, p

    best_val = -1.0
    metrics_out: Dict[str, float] = {}

    for epoch in range(epochs):
        model.train()
        random.shuffle(train_pairs)
        total_loss = 0.0
        n_batches = 0
        batch_size = int(ml['BATCH_SIZE'])
        for i in range(0, len(train_pairs), batch_size):
            batch = train_pairs[i : i + batch_size]
            if not batch:
                continue
            users = torch.tensor([b[0] for b in batch], device=device, dtype=torch.long)
            pos = torch.tensor([b[1] for b in batch], device=device, dtype=torch.long)
            negs = []
            for u, pp in batch:
                for _ in range(neg_ratio):
                    n = random.choice(all_products)
                    while n in user_pos.get(u, set()) or n == pp:
                        n = random.choice(all_products)
                    negs.append(n)
            neg = torch.tensor(negs, device=device, dtype=torch.long).view(len(batch), neg_ratio)

            opt.zero_grad()
            u_emb, p_emb = forward_emb()
            u_v = u_emb[users]
            pos_v = p_emb[pos]
            loss_acc = None
            for k in range(neg_ratio):
                neg_v = p_emb[neg[:, k]]
                pos_s = (u_v * pos_v).sum(dim=-1)
                neg_s = (u_v * neg_v).sum(dim=-1)
                diff = pos_s - neg_s
                bpr = -F.logsigmoid(diff).mean()
                loss_acc = bpr if loss_acc is None else loss_acc + bpr
            assert loss_acc is not None
            loss = loss_acc / neg_ratio
            loss.backward()
            opt.step()
            total_loss += float(loss.item())
            n_batches += 1

        # Validation: Recall@K via FAISS on product side
        model.eval()
        with torch.no_grad():
            u_emb, p_emb = model.user_product_embeddings(data, ew)
            u_np = u_emb.cpu().numpy()
            p_np = p_emb.cpu().numpy()
            itos = mappings['product_itos']
            faiss_idx = ProductFaissIndex()
            faiss_idx.build(p_np, [int(x) for x in itos])

            k_eval = int(ml['EVAL_K'])
            recalls = []
            precs = []
            val_users: Dict[int, Set[int]] = {}
            for u, p in val_pairs:
                val_users.setdefault(u, set()).add(p)
            for u_idx, rel in val_users.items():
                q = u_np[u_idx]
                rec_rows, _ = faiss_idx.search(q, k_eval + 20)
                rec_pidx = []
                for ext_pid in rec_rows:
                    ii = product_stoi.get(ext_pid)
                    if ii is not None and ii not in rel:
                        rec_pidx.append(ext_pid)
                    if len(rec_pidx) >= k_eval:
                        break
                rel_ext = {itos[i] for i in rel}
                recalls.append(recall_at_k(rec_pidx, set(rel_ext), k_eval))
                precs.append(precision_at_k(rec_pidx, set(rel_ext), k_eval))

            val_recall = float(np.mean(recalls)) if recalls else 0.0
            val_prec = float(np.mean(precs)) if precs else 0.0
            metrics_out = {'recall@k': val_recall, 'precision@k': val_prec, 'epoch': float(epoch)}

        logger.info(
            'Epoch %d/%d loss=%.4f recall@%d=%.4f precision@%d=%.4f',
            epoch + 1,
            epochs,
            total_loss / max(n_batches, 1),
            k_eval,
            val_recall,
            k_eval,
            val_prec,
        )
        if val_recall > best_val:
            best_val = val_recall
            ckpt = Path(ml['MODEL_PATH'])
            ckpt.parent.mkdir(parents=True, exist_ok=True)
            torch.save(
                {
                    'model_state': model.state_dict(),
                    'num_nodes_dict': _num_nodes_dict(data),
                    'hidden_dim': hidden,
                    'out_dim': out_dim,
                    'metrics': metrics_out,
                },
                ckpt,
            )

    return model, metrics_out


def build_faiss_from_best_checkpoint(data: HeteroData, mappings: Dict[str, Any], device: torch.device) -> None:
    """Nạp checkpoint tốt nhất, forward toàn đồ thị, xây FAISS trên embedding sản phẩm."""
    ml = settings.RECOMMENDATION_ML
    ckpt_path = Path(ml['MODEL_PATH'])
    if not ckpt_path.exists():
        raise RuntimeError('Không tìm thấy checkpoint model sau huấn luyện.')
    try:
        ckpt = torch.load(ckpt_path, map_location=device, weights_only=False)
    except TypeError:
        ckpt = torch.load(ckpt_path, map_location=device)
    model = HeteroGraphSAGEModel(
        int(ckpt['hidden_dim']),
        int(ckpt['out_dim']),
        ckpt['num_nodes_dict'],
    )
    model.load_state_dict(ckpt['model_state'])
    model.to(device)
    model.eval()
    d = data.to(device)
    ew = {k: v.to(device) for k, v in edge_weight_dict_from_data(d).items()}
    with torch.no_grad():
        _, p_emb = model.user_product_embeddings(d, ew)
    p_np = p_emb.cpu().numpy()
    itos = mappings['product_itos']
    faiss_idx = ProductFaissIndex()
    faiss_idx.build(p_np, [int(x) for x in itos])
    faiss_idx.save(Path(ml['FAISS_DIR']))


def run_full_training_pipeline() -> Dict[str, Any]:
    """Rebuild graph → heterodata → train → FAISS (gọi từ API retrain / management command)."""
    ml = settings.RECOMMENDATION_ML
    device = torch.device('cuda' if torch.cuda.is_available() and ml['USE_CUDA'] else 'cpu')

    builder = GraphBuilder(NetworkXGraphStorage())
    builder.build_from_database(full_rebuild=True)
    builder.save()

    data, mappings = storage_to_heterodata(builder.storage)
    bundle_path = Path(ml['HETERODATA_PATH'])
    mappings_path = Path(ml['MAPPINGS_JSON_PATH'])
    save_heterodata(data, mappings, bundle_path, mappings_path)

    data, mappings = load_heterodata_bundle(bundle_path)
    data = data.to(device)

    _, metrics = train_gnn(
        data,
        mappings,
        epochs=int(ml['TRAIN_EPOCHS']),
        lr=float(ml['LEARNING_RATE']),
        device=device,
        val_ratio=float(ml['VAL_RATIO']),
    )

    data_cpu, mappings = load_heterodata_bundle(bundle_path)
    build_faiss_from_best_checkpoint(data_cpu, mappings, device)

    from .realtime_graph import reset_graph_builder

    reset_graph_builder()
    return {'status': 'ok', 'metrics': metrics}
