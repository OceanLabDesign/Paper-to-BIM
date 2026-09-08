"""Geometry and semantic constraints used by deterministic solvers."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Mapping, Optional, Tuple

from .provenance import ProvenanceRef


class ConstraintStrength(str, Enum):
    HARD = "hard"
    SOFT = "soft"


@dataclass(frozen=True)
class Constraint:
    id: str
    type: str
    targets: Tuple[str, ...]
    strength: ConstraintStrength
    confidence: float
    value: Any = None
    unit: Optional[str] = None
    provenance: Tuple[ProvenanceRef, ...] = field(default_factory=tuple)
    attributes: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.id:
            raise ValueError("Constraint.id must not be empty")
        if not self.type:
            raise ValueError("Constraint.type must not be empty")
        if not self.targets:
            raise ValueError("Constraint.targets must not be empty")
        if not 0.0 <= self.confidence <= 1.0:
            raise ValueError("Constraint.confidence must be between 0 and 1")

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "type": self.type,
            "targets": list(self.targets),
            "strength": self.strength.value,
            "confidence": self.confidence,
            "value": self.value,
            "unit": self.unit,
            "provenance": [p.to_dict() for p in self.provenance],
            "attributes": dict(self.attributes),
        }

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> "Constraint":
        return cls(
            id=str(data["id"]),
            type=str(data["type"]),
            targets=tuple(str(v) for v in data["targets"]),
            strength=ConstraintStrength(str(data["strength"])),
            confidence=float(data["confidence"]),
            value=data.get("value"),
            unit=data.get("unit"),
            provenance=tuple(ProvenanceRef.from_dict(p) for p in data.get("provenance", ())),
            attributes=data.get("attributes", {}),
        )
