"""
Lưu trữ đồ thị — MVP: NetworkX; interface sẵn sàng chuyển Neo4j sau.

Neo4j: triển khai GraphStorage với các phương thức cùng chữ ký, thay thế
NetworkXGraphStorage trong settings / DI.
"""
from __future__ import annotations

import pickle
from abc import ABC, abstractmethod
from enum import Enum
from pathlib import Path
from typing import Any, Dict, Iterator, List, Optional, Tuple

import networkx as nx


class NodeType(str, Enum):
    """Loại nút trong knowledge graph dị thể."""
    USER = 'user'
    PRODUCT = 'product'
    CATEGORY = 'category'
    QUERY = 'query'


# Khóa nút canonical: (NodeType, id) — id là int (user/product/category) hoặc str (query text đã chuẩn hoá)
NodeKey = Tuple[NodeType, Any]


class GraphStorage(ABC):
    """Hợp đồng lưu trữ đồ thị có hướng, có trọng số cạnh."""

    @abstractmethod
    def clear(self) -> None:
        pass

    @abstractmethod
    def add_edge(
        self,
        src: NodeKey,
        dst: NodeKey,
        edge_type: str,
        weight: float = 1.0,
        accumulate: bool = True,
    ) -> None:
        """Thêm hoặc cộng dồn trọng số cạnh (cùng edge_type)."""

    @abstractmethod
    def nodes_iter(self) -> Iterator[NodeKey]:
        pass

    @abstractmethod
    def edges_iter(self) -> Iterator[Tuple[NodeKey, NodeKey, str, float]]:
        """Yield (src, dst, edge_type, weight)."""

    @abstractmethod
    def neighbors(self, node: NodeKey, edge_type: Optional[str] = None) -> List[Tuple[NodeKey, float, str]]:
        """Các nút kề (đi ra) kèm trọng số và loại cạnh."""

    @abstractmethod
    def save(self, path: Path) -> None:
        pass

    @abstractmethod
    def load(self, path: Path) -> None:
        pass


class NetworkXGraphStorage(GraphStorage):
    """
    Đồ thị có hướng; mỗi cạnh có attr: edge_type, weight.
    Dùng MultiDiGraph để cho phép nhiều quan hệ song song giữa hai nút (hiếm).
    """

    def __init__(self) -> None:
        self._g: nx.MultiDiGraph = nx.MultiDiGraph()

    def clear(self) -> None:
        self._g.clear()

    def add_edge(
        self,
        src: NodeKey,
        dst: NodeKey,
        edge_type: str,
        weight: float = 1.0,
        accumulate: bool = True,
    ) -> None:
        self._g.add_node(src, nt=src[0].value)
        self._g.add_node(dst, nt=dst[0].value)
        key = edge_type
        if self._g.has_edge(src, dst, key=key):
            if accumulate:
                self._g[src][dst][key]['weight'] += weight
        else:
            self._g.add_edge(src, dst, key=key, edge_type=edge_type, weight=float(weight))

    def nodes_iter(self) -> Iterator[NodeKey]:
        yield from self._g.nodes()

    def edges_iter(self) -> Iterator[Tuple[NodeKey, NodeKey, str, float]]:
        for u, v, k, data in self._g.edges(keys=True, data=True):
            yield u, v, data.get('edge_type', k), float(data.get('weight', 1.0))

    def neighbors(self, node: NodeKey, edge_type: Optional[str] = None) -> List[Tuple[NodeKey, float, str]]:
        if node not in self._g:
            return []
        out: List[Tuple[NodeKey, float, str]] = []
        for _, v, k, data in self._g.out_edges(node, keys=True, data=True):
            et = data.get('edge_type', k)
            if edge_type is not None and et != edge_type:
                continue
            out.append((v, float(data.get('weight', 1.0)), et))
        return out

    def save(self, path: Path) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, 'wb') as f:
            pickle.dump(self._g, f, protocol=pickle.HIGHEST_PROTOCOL)

    def load(self, path: Path) -> None:
        with open(path, 'rb') as f:
            self._g = pickle.load(f)

    @property
    def raw_graph(self) -> nx.MultiDiGraph:
        return self._g


class Neo4jGraphStorage(GraphStorage):
    """
    Stub cho mở rộng Neo4j: triển khai Cypher MERGE / cộng dồn weight tại đây.
    """

    def clear(self) -> None:
        raise NotImplementedError('Neo4jGraphStorage: implement with neo4j driver')

    def add_edge(self, src: NodeKey, dst: NodeKey, edge_type: str, weight: float = 1.0, accumulate: bool = True) -> None:
        raise NotImplementedError

    def nodes_iter(self) -> Iterator[NodeKey]:
        raise NotImplementedError

    def edges_iter(self) -> Iterator[Tuple[NodeKey, NodeKey, str, float]]:
        raise NotImplementedError

    def neighbors(self, node: NodeKey, edge_type: Optional[str] = None) -> List[Tuple[NodeKey, float, str]]:
        raise NotImplementedError

    def save(self, path: Path) -> None:
        raise NotImplementedError('Neo4j persists in database, not pickle')

    def load(self, path: Path) -> None:
        raise NotImplementedError
