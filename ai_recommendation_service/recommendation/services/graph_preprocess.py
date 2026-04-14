"""
Chuyển GraphStorage (NetworkX) → PyTorch Geometric HeteroData.

Bao gồm: edge_index + edge_weight theo từng loại cạnh, cả cạnh nghịch để message passing hai phía.
"""
from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any, Dict, List, Tuple

import torch
from torch_geometric.data import HeteroData

from .graph_storage import GraphStorage, NodeKey, NodeType

logger = logging.getLogger(__name__)

# Định nghĩa tên cạnh PyG (source, relation, target)
EDGE_SPECS: List[Tuple[str, str, str]] = [
    ('user', 'interacts', 'product'),
    ('product', 'rev_interacts', 'user'),
    ('user', 'searches', 'query'),
    ('query', 'rev_searches', 'user'),
    ('product', 'in_category', 'category'),
    ('category', 'rev_in_category', 'product'),
    ('product', 'co_click', 'product'),
]


def _collect_nodes(storage: GraphStorage) -> Dict[NodeType, List[Any]]:
    by: Dict[NodeType, set] = {t: set() for t in NodeType}
    for nk in storage.nodes_iter():
        by[nk[0]].add(nk[1])
    return {t: sorted(by[t]) for t in NodeType}


def _stoi(ids: List[Any]) -> Dict[Any, int]:
    return {x: i for i, x in enumerate(ids)}


def storage_to_heterodata(storage: GraphStorage) -> Tuple[HeteroData, Dict[str, Any]]:
    """
    Trả về (HeteroData, mappings) — mappings gồm *_stoi / *_itos (JSON-serializable).
    """
    nodes = _collect_nodes(storage)
    mappings: Dict[str, Any] = {}
    stoi: Dict[NodeType, Dict[Any, int]] = {}
    itos: Dict[NodeType, List[Any]] = {}
    for nt in NodeType:
        ids = nodes[nt]
        itos[nt] = ids
        stoi[nt] = _stoi(ids)
        # Khóa gốc (int / str) để torch.save; file JSON dùng default=str
        mappings[f'{nt.value}_stoi'] = dict(stoi[nt])
        mappings[f'{nt.value}_itos'] = list(ids)

    data = HeteroData()
    for nt in NodeType:
        data[nt.value].num_nodes = len(itos[nt])

    # Accumulate edges per PyG edge_type from storage triples
    raw_edges: Dict[Tuple[str, str, str], List[Tuple[int, int, float]]] = {}

    def add_py_edge(et: Tuple[str, str, str], si: int, di: int, w: float) -> None:
        raw_edges.setdefault(et, []).append((si, di, w))

    for src, dst, etype, w in storage.edges_iter():
        st, sid = src
        dt, did = dst
        if etype == 'interacts':
            if st == NodeType.USER and dt == NodeType.PRODUCT:
                su = stoi[NodeType.USER][sid]
                pv = stoi[NodeType.PRODUCT][did]
                add_py_edge(('user', 'interacts', 'product'), su, pv, w)
                add_py_edge(('product', 'rev_interacts', 'user'), pv, su, w)
        elif etype == 'searches':
            if st == NodeType.USER and dt == NodeType.QUERY:
                su = stoi[NodeType.USER][sid]
                qi = stoi[NodeType.QUERY][did]
                add_py_edge(('user', 'searches', 'query'), su, qi, w)
                add_py_edge(('query', 'rev_searches', 'user'), qi, su, w)
        elif etype == 'in_category':
            if st == NodeType.PRODUCT and dt == NodeType.CATEGORY:
                pi = stoi[NodeType.PRODUCT][sid]
                ci = stoi[NodeType.CATEGORY][did]
                add_py_edge(('product', 'in_category', 'category'), pi, ci, w)
                add_py_edge(('category', 'rev_in_category', 'product'), ci, pi, w)
        elif etype == 'co_click':
            if st == NodeType.PRODUCT and dt == NodeType.PRODUCT:
                a = stoi[NodeType.PRODUCT][sid]
                b = stoi[NodeType.PRODUCT][did]
                add_py_edge(('product', 'co_click', 'product'), a, b, w)

    for et in EDGE_SPECS:
        triple = raw_edges.get(et, [])
        if not triple:
            edge_index = torch.empty((2, 0), dtype=torch.long)
            edge_weight = torch.empty((0,), dtype=torch.float32)
        else:
            srcs = [t[0] for t in triple]
            dsts = [t[1] for t in triple]
            weights = [t[2] for t in triple]
            edge_index = torch.tensor([srcs, dsts], dtype=torch.long)
            edge_weight = torch.tensor(weights, dtype=torch.float32)
        data[et].edge_index = edge_index
        data[et].edge_weight = edge_weight

    logger.info(
        'HeteroData: users=%d products=%d categories=%d queries=%d',
        data['user'].num_nodes,
        data['product'].num_nodes,
        data['category'].num_nodes,
        data['query'].num_nodes,
    )
    return data, mappings


def _hetero_to_cpu(d: HeteroData) -> HeteroData:
    out = d.clone()
    for nt in out.node_types:
        st = out[nt]
        for key, val in st.items():
            if torch.is_tensor(val):
                st[key] = val.cpu()
    for et in out.edge_types:
        st = out[et]
        for key, val in st.items():
            if torch.is_tensor(val):
                st[key] = val.cpu()
    return out


def save_heterodata(data: HeteroData, mappings: Dict[str, Any], path: Path, mappings_path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    torch.save({'data': _hetero_to_cpu(data), 'mappings': mappings}, path)
    mappings_path.parent.mkdir(parents=True, exist_ok=True)
    with open(mappings_path, 'w', encoding='utf-8') as f:
        json.dump(mappings, f, indent=2, ensure_ascii=False, default=str)


def edge_weight_dict_from_data(data: HeteroData) -> Dict[Tuple[str, str, str], torch.Tensor]:
    """Trích edge_weight cho các cạnh không rỗng (dùng cho forward GNN)."""
    out: Dict[Tuple[str, str, str], torch.Tensor] = {}
    for et in EDGE_SPECS:
        if et not in data.edge_types or data[et].num_edges == 0:
            continue
        out[et] = data[et].edge_weight.to(dtype=torch.float32)
    return out


def load_heterodata_bundle(path: Path) -> Tuple[HeteroData, Dict[str, Any]]:
    try:
        bundle = torch.load(path, map_location='cpu', weights_only=False)
    except TypeError:
        bundle = torch.load(path, map_location='cpu')
    return bundle['data'], bundle['mappings']
