"""Canonical reconstructed entities."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Mapping, Tuple

from .provenance import ProvenanceRef


class EntityState(str, Enum):
    INFERRED = "inferred"
    CONFIRMED = "confirmed"
    AMBIGUOUS = "ambiguous"
    CONFLICTED = "conflicted"


@dataclass(frozen=True)
class Entity:
    id: str
    type: str
    geometry: Mapping[str, Any]
    confidence: float
    state: EntityState = EntityState.INFERRED
    provenance: Tuple[ProvenanceRef, ...] = field(default_factory=tuple)
    attributes: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.id:
            raise ValueError("Entity.id must not be empty")
        if not self.type:
            raise ValueError("Entity.type must not be empty")
        if not 0.0 <= self.confidence <= 1.0:
            raise ValueError("Entity.confidence must be between 0 and 1")

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "type": self.type,
            "geometry": dict(self.geometry),
            "confidence": self.confidence,
            "state": self.state.value,
            "provenance": [p.to_dict() for p in self.provenance],
            "attributes": dict(self.attributes),
        }

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> "Entity":
        return cls(
            id=str(data["id"]),
            type=str(data["type"]),
            geometry=data["geometry"],
            confidence=float(data["confidence"]),
            state=EntityState(str(data.get("state", EntityState.INFERRED.value))),
            provenance=tuple(ProvenanceRef.from_dict(p) for p in data.get("provenance", ())),
            attributes=data.get("attributes", {}),
        )
