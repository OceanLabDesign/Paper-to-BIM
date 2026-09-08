"""Semantic grid-coordinate solver tool.

The agent supplies dimension facts; deterministic code returns coordinates and
conflicts. The model never invents final CAD coordinates itself.
"""

from __future__ import annotations

from typing import Any, Mapping

from agent_runtime.tools import ToolDefinition, ToolResult
from solver import GridDistance, solve_grid_axis_positions


def _solve(arguments: Mapping[str, Any]) -> ToolResult:
    distances = tuple(
        GridDistance(
            start=str(item["start"]),
            end=str(item["end"]),
            distance=float(item["distance_mm"]),
            constraint_id=str(item["constraint_id"]),
        )
        for item in arguments["distances"]
    )
    solution = solve_grid_axis_positions(
        distances,
        origin_axis=str(arguments["origin_axis"]),
        origin_value=float(arguments.get("origin_value_mm", 0.0)),
    )
    conflicts = [
        {
            "axis": c.axis,
            "expected_mm": c.expected,
            "computed_mm": c.computed,
            "delta_mm": c.delta,
            "constraint_id": c.constraint_id,
        }
        for c in solution.conflicts
    ]
    return ToolResult(
        content={
            "unit": "mm",
            "positions": dict(solution.positions),
            "solved": solution.solved,
            "conflicts": conflicts,
        },
        result_refs=tuple(d.constraint_id for d in distances),
    )


def make_grid_solver_tool() -> ToolDefinition:
    return ToolDefinition(
        name="solve_grid_coordinates",
        description=(
            "Solve real 1:1 grid-axis coordinates in millimetres from explicit "
            "dimension constraints. Reports contradictory dimensions instead of "
            "averaging or guessing."
        ),
        category="solver",
        mutates_domain=False,
        input_schema={
            "type": "object",
            "properties": {
                "origin_axis": {"type": "string"},
                "origin_value_mm": {"type": "number", "default": 0},
                "distances": {
                    "type": "array",
                    "minItems": 1,
                    "items": {
                        "type": "object",
                        "properties": {
                            "start": {"type": "string"},
                            "end": {"type": "string"},
                            "distance_mm": {"type": "number", "exclusiveMinimum": 0},
                            "constraint_id": {"type": "string"},
                        },
                        "required": ["start", "end", "distance_mm", "constraint_id"],
                        "additionalProperties": False,
                    },
                },
            },
            "required": ["origin_axis", "distances"],
            "additionalProperties": False,
        },
        handler=_solve,
    )
