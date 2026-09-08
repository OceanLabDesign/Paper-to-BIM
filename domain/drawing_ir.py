"""Canonical intermediate representation for reconstructed drawings."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Any, Mapping, Tuple

from .conflict import Conflict
from .constraint import Constraint
from .entity import Entity
from .observation import Observation


@dataclass(frozen=True)
class DrawingIR:
    """Single source of truth between reconstruction and exporters."""

    schema_version: str = "1.0"
    units: str = "mm"
    observations: Tuple[Observation, ...] = field(default_factory=tuple)
    constraints: Tuple[Constraint, ...] = field(default_factory=tuple)
    entities: Tuple[Entity, ...] = field(default_factory=tuple)
    conflicts: Tuple[Conflict, ...] = field(default_factory=tuple)
    metadata: Mapping[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "units": self.units,
            "observations": [o.to_dict() for o in self.observations],
            "constraints": [c.to_dict() for c in self.constraints],
            "entities": [e.to_dict() for e in self.entities],
            "conflicts": [c.to_dict() for c in self.conflicts],
            "metadata": dict(self.metadata),
        }

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> "DrawingIR":
        return cls(
            schema_version=str(data.get("schema_version", "1.0")),
            units=str(data.get("units", "mm")),
            observations=tuple(Observation.from_dict(v) for v in data.get("observations", ())),
            constraints=tuple(Constraint.from_dict(v) for v in data.get("constraints", ())),
            entities=tuple(Entity.from_dict(v) for v in data.get("entities", ())),
            conflicts=tuple(Conflict.from_dict(v) for v in data.get("conflicts", ())),
            metadata=data.get("metadata", {}),
        )

    def to_json(self, *, indent: int | None = 2) -> str:
        """Serialize deterministically for artifacts, diffs, and cache keys."""
        return json.dumps(
            self.to_dict(),
            ensure_ascii=False,
            indent=indent,
            sort_keys=True,
            separators=None if indent is not None else (",", ":"),
        )

    @classmethod
    def from_json(cls, payload: str) -> "DrawingIR":
        return cls.from_dict(json.loads(payload))
