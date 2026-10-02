"""Asset Registry bounded context: the location / asset hierarchy.

EAM systems model plants as trees, e.g. ``SITE-01 / AREA-BOILER / SYS-FEEDWATER / PUMP-101 / MOTOR-101``.
Each node stores a *materialised path* (the PostgreSQL schema uses ``ltree``), which makes
"everything under this system" a single indexed prefix query and allows cost and downtime to be
rolled up the tree.
"""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass
from decimal import Decimal


@dataclass(frozen=True)
class Node:
    id: str
    path: str  # dot-separated ancestor ids including self, e.g. "SITE01.BOILER.FW.P101"
    name: str
    criticality: str = "C"  # A (critical) .. C (low)

    @property
    def parent_path(self) -> str | None:
        return self.path.rsplit(".", 1)[0] if "." in self.path else None

    @property
    def depth(self) -> int:
        return self.path.count(".") + 1


class Hierarchy:
    def __init__(self, nodes: Iterable[Node]) -> None:
        self._by_path: dict[str, Node] = {}
        for n in nodes:
            if n.path.rsplit(".", 1)[-1] != n.id:
                raise ValueError(f"path of {n.id} must end with its own id")
            self._by_path[n.path] = n
        for n in self._by_path.values():
            if n.parent_path and n.parent_path not in self._by_path:
                raise ValueError(f"{n.id}: parent {n.parent_path} is missing")
        self._by_id = {n.id: n for n in self._by_path.values()}

    def node(self, node_id: str) -> Node:
        return self._by_id[node_id]

    def descendants(self, node_id: str, include_self: bool = True) -> list[Node]:
        root = self._by_id[node_id].path
        return sorted(
            (
                n
                for n in self._by_path.values()
                if n.path == root and include_self or n.path.startswith(root + ".")
            ),
            key=lambda n: n.path,
        )

    def ancestors(self, node_id: str) -> list[Node]:
        parts = self._by_id[node_id].path.split(".")
        return [self._by_path[".".join(parts[:i])] for i in range(1, len(parts))]

    def rollup(self, values: dict[str, Decimal]) -> dict[str, Decimal]:
        """Sum a per-node value (cost, downtime hours) into every ancestor."""
        totals: dict[str, Decimal] = {n.id: Decimal("0") for n in self._by_path.values()}
        for node_id, value in values.items():
            totals[node_id] += value
            for anc in self.ancestors(node_id):
                totals[anc.id] += value
        return totals

    def effective_criticality(self, node_id: str) -> str:
        """A component is at least as critical as its most critical ancestor system (A < B < C)."""
        chain = [*self.ancestors(node_id), self._by_id[node_id]]
        return min(n.criticality for n in chain)
