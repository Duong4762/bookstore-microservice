"""
Heterogeneous GraphSAGE (PyTorch Geometric) — message passing có edge_weight.

Mỗi layer: HeteroConv gồm các SAGEConv theo từng loại cạnh; truyền edge_weight
vào SAGEConv (PyG >= 2.0 hỗ trợ).
"""
from __future__ import annotations

from typing import Dict, List, Optional, Tuple

import torch
import torch.nn.functional as F
from torch import nn
from torch_geometric.data import HeteroData
from torch_geometric.nn import HeteroConv
from torch_geometric.nn.conv import MessagePassing

from .graph_preprocess import EDGE_SPECS

NodeTypes = ('user', 'product', 'category', 'query')


def _hetero_metadata() -> Tuple[List, List]:
    node_types = list(NodeTypes)
    edge_types = [tuple(e) for e in EDGE_SPECS]
    return node_types, edge_types


class WeightedSAGEConv(MessagePassing):
    """
    GraphSAGE-style conv có hỗ trợ `edge_weight`.

    Công thức (mean aggregation):
      m_{j→i} = w_{j,i} * W_r x_j
      h_i = W_l x_i + mean_j(m_{j→i})
    """

    def __init__(self, in_channels: Tuple[int, int], out_channels: int) -> None:
        super().__init__(aggr='mean')
        in_src, in_dst = in_channels
        self.lin_l = nn.Linear(in_dst, out_channels, bias=True)
        self.lin_r = nn.Linear(in_src, out_channels, bias=False)

    def forward(
        self,
        x: Tuple[torch.Tensor, torch.Tensor],
        edge_index: torch.Tensor,
        edge_weight: Optional[torch.Tensor] = None,
    ) -> torch.Tensor:
        x_src, x_dst = x
        out = self.propagate(edge_index, x=x_src, edge_weight=edge_weight, size=(x_src.size(0), x_dst.size(0)))
        out = out + self.lin_l(x_dst)
        return out

    def message(self, x_j: torch.Tensor, edge_weight: Optional[torch.Tensor]) -> torch.Tensor:
        msg = self.lin_r(x_j)
        if edge_weight is None:
            return msg
        return msg * edge_weight.view(-1, 1)


class HeteroGraphSAGEModel(nn.Module):
    """
    Hai tầng HeteroConv + GraphSAGE; đầu ra embedding user / product (chuẩn hoá L2).
    """

    def __init__(self, hidden_dim: int, out_dim: int, num_nodes_dict: Dict[str, int]) -> None:
        super().__init__()
        self.hidden_dim = hidden_dim
        self.out_dim = out_dim
        self.node_types = list(NodeTypes)
        _, edge_types = _hetero_metadata()

        self.emb = nn.ModuleDict(
            {nt: nn.Embedding(num_nodes_dict[nt], hidden_dim) for nt in self.node_types}
        )
        nn.init.xavier_uniform_(self.emb['user'].weight)
        nn.init.xavier_uniform_(self.emb['product'].weight)
        nn.init.xavier_uniform_(self.emb['category'].weight)
        nn.init.xavier_uniform_(self.emb['query'].weight)

        convs1 = {et: WeightedSAGEConv((hidden_dim, hidden_dim), hidden_dim) for et in edge_types}
        convs2 = {et: WeightedSAGEConv((hidden_dim, hidden_dim), out_dim) for et in edge_types}
        self.conv1 = HeteroConv(convs1, aggr='sum')
        self.conv2 = HeteroConv(convs2, aggr='sum')

    def _x_dict(self) -> Dict[str, torch.Tensor]:
        return {nt: self.emb[nt].weight for nt in self.node_types}

    def forward(
        self,
        data: HeteroData,
        edge_weight_dict: Dict[Tuple[str, str, str], torch.Tensor],
    ) -> Dict[str, torch.Tensor]:
        x_dict = self._x_dict()
        ei = {}
        for k in EDGE_SPECS:
            if k not in data.edge_types or data[k].num_edges == 0:
                continue
            ei[k] = data[k].edge_index
        ew1 = {k: edge_weight_dict[k] for k in ei if k in edge_weight_dict}
        x_dict = self.conv1(x_dict, ei, edge_weight_dict=ew1)
        x_dict = {k: F.relu(v) for k, v in x_dict.items()}
        ew2 = {k: edge_weight_dict[k] for k in ei if k in edge_weight_dict}
        x_dict = self.conv2(x_dict, ei, edge_weight_dict=ew2)
        return x_dict

    @torch.no_grad()
    def user_product_embeddings(
        self,
        data: HeteroData,
        edge_weight_dict: Dict[Tuple[str, str, str], torch.Tensor],
    ) -> Tuple[torch.Tensor, torch.Tensor]:
        self.eval()
        out = self.forward(data, edge_weight_dict)
        u = F.normalize(out['user'], dim=-1)
        p = F.normalize(out['product'], dim=-1)
        return u, p
