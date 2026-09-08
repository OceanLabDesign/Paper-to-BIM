"""Solve 1D grid-axis coordinates from explicit dimension constraints.

This is the first production-oriented in-scale solver. It does not inspect pixels.
Distances are expressed in DrawingIR units (millimetres by default).
"""

from __future__ import annotations

from dataclasses import dataclass
from math import isclose
from typing import Iterable, Mapping


@dataclass(frozen=True)
class GridDistance:
    start: str
    end: str
    distance: float
    constraint_id: str

    def __post_init__(self) -> None:
        if not self.start or not self.end:
            raise ValueError("GridDistance endpoints must not be empty")
        if self.start == self.end:
            raise ValueError("GridDistance endpoints must differ")
        if self.distance <= 0:
            raise ValueError("GridDistance.distance must be > 0")


@dataclass(frozen=True)
class GridConflict:
    axis: str
    expected: float
    computed: float
    constraint_id: str

    @property
    def delta(self) -> float:
        return self.computed - self.expected


@dataclass(frozen=True)
class GridSolution:
    positions: Mapping[str, float]
    conflicts: tuple[GridConflict, ...] = ()

    @property
    def solved(self) -> bool:
        return not self.conflicts


def solve_grid_axis_positions(
    distances: Iterable[GridDistance],
    *,
    origin_axis: str,
    origin_value: float = 0.0,
    tolerance: float = 1e-6,
) -> GridSolution:
    """Propagate exact coordinates through a dimension graph.

    Each distance is directional: ``end = start + distance``. The graph may contain
    redundant total dimensions. Redundancy is useful because disagreement becomes
    an explicit conflict instead of being averaged away.
    """

    edges = tuple(distances)
    positions: dict[str, float] = {origin_axis: float(origin_value)}
    conflicts: list[GridConflict] = []

    changed = True
    while changed:
        changed = False
        for edge in edges:
            start_known = edge.start in positions
            end_known = edge.end in positions

            if start_known and not end_known:
                positions[edge.end] = positions[edge.start] + edge.distance
                changed = True
                continue

            if end_known and not start_known:
                positions[edge.start] = positions[edge.end] - edge.distance
                changed = True
                continue

            if start_known and end_known:
                computed_end = positions[edge.start] + edge.distance
                if not isclose(computed_end, positions[edge.end], abs_tol=tolerance, rel_tol=0.0):
                    conflict = GridConflict(
                        axis=edge.end,
                        expected=positions[edge.end],
                        computed=computed_end,
                        constraint_id=edge.constraint_id,
                    )
                    if conflict not in conflicts:
                        conflicts.append(conflict)

    unresolved_axes = {
        endpoint
        for edge in edges
        for endpoint in (edge.start, edge.end)
        if endpoint not in positions
    }
    if unresolved_axes:
        raise ValueError(
            "Dimension graph is disconnected from origin axis "
            f"{origin_axis!r}; unresolved: {sorted(unresolved_axes)}"
        )

    return GridSolution(positions=dict(sorted(positions.items())), conflicts=tuple(conflicts))
