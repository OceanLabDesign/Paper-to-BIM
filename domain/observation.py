"""Observation: what the source drawing appears to contain."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Mapping, Optional, Tuple

from .provenance import ProvenanceRef


@dataclass(frozen=True)
class Observation:
    """Evidence-backed claim extracted from a source drawing.

    Observation is deliberately not truth.  It may be contradicted, superseded,
    or left unresolved without corrupting downstream geometry.
    """

    id: str
    type: str
    confidence: float
    value: Any = None
    unit: Optional[str] = None
    geometry: Optional[Mapping[str, Any]] = None
    provenance: Tuple[ProvenanceRef, ...] = field(default_factory=tuple)
    attributes: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.id:
            raise ValueError("Observation.id must not be empty")
        if not self.type:
            raise ValueError("Observation.type must not be empty")
        if not 0.0 <= self.confidence <= 1.0:
            raise ValueError("Observation.confidence must be between 0 and 1")

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "type": self.type,
            "confidence": self.confidence,
            "value": self.value,
            "unit": self.unit,
            "geometry": dict(self.geometry) if self.geometry is not None else None,
            "provenance": [p.to_dict() for p in self.provenance],
            "attributes": dict(self.attributes),
        }

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> "Observation":
        return cls(
            id=str(data["id"]),
            type=str(data["type"]),
            confidence=float(data["confidence"]),
            value=data.get("value"),
            unit=data.get("unit"),
            geometry=data.get("geometry"),
            provenance=tuple(ProvenanceRef.from_dict(p) for p in data.get("provenance", ())),
            attributes=data.get("attributes", {}),
        )
