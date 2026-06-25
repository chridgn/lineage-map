from __future__ import annotations
from dataclasses import dataclass, field


@dataclass
class ColumnNode:
    id: str            # "model.project.orders.revenue"
    model: str         # "orders"
    column: str        # "revenue"
    upstream: list[str] = field(default_factory=list)    # ColumnNode ids
    downstream: list[str] = field(default_factory=list)  # ColumnNode ids

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "model": self.model,
            "column": self.column,
            "upstream": self.upstream,
            "downstream": self.downstream,
        }


@dataclass
class LineageGraph:
    nodes: dict[str, ColumnNode] = field(default_factory=dict)

    def add_node(self, node: ColumnNode) -> None:
        self.nodes[node.id] = node

    def get_node(self, node_id: str) -> ColumnNode | None:
        return self.nodes.get(node_id)

    def upstream_of(self, node_id: str) -> list[ColumnNode]:
        node = self.nodes.get(node_id)
        if not node:
            return []
        return [self.nodes[uid] for uid in node.upstream if uid in self.nodes]

    def downstream_of(self, node_id: str) -> list[ColumnNode]:
        node = self.nodes.get(node_id)
        if not node:
            return []
        return [self.nodes[did] for did in node.downstream if did in self.nodes]

    def to_dict(self) -> dict:
        return {"nodes": {nid: n.to_dict() for nid, n in self.nodes.items()}}

    def find_by_column(self, column: str) -> list[ColumnNode]:
        return [n for n in self.nodes.values() if n.column.lower() == column.lower()]
