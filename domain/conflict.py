"""Explicit unresolved contradictions discovered during reconstruction."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Mapping, Tuple

from .provenance import ProvenanceRef


class ConflictStatus(str, Enum):
    OPEN = "open"
    RESOLVED = "resolved"
    ACCEPTED_AS_IS = "accepted_as_is"


@dataclass(frozen=True)
class Conflict:
    id: str
    kind: str
    description: str
    involved_ids: Tuple[str, ...]
    severity: str = "warning"
    status: ConflictStatus = ConflictStatus.OPEN
    provenance: Tuple[ProvenanceRef, ...] = field(default_factory=tuple)
    attributes: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.id:
            raise ValueError("Conflict.id must not be empty")
        if not self.kind:
            raise ValueError("Conflict.kind must not be empty")
        if not self.involved_ids:
            raise ValueError("Conflict.involved_ids must not be empty")

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "kind": self.kind,
            "description": self.description,
            "involved_ids": list(self.involved_ids),
            "severity": self.severity,
            "status": self.status.value,
            "provenance": [p.to_dict() for p in self.provenance],
            "attributes": dict(self.attributes),
        }

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> "Conflict":
        return cls(
            id=str(data["id"]),
            kind=str(data["kind"]),
            description=str(data.get("description", "")),
            involved_ids=tuple(str(v) for v in data["involved_ids"]),
            severity=str(data.get("severity", "warning")),
            status=ConflictStatus(str(data.get("status", ConflictStatus.OPEN.value))),
            provenance=tuple(ProvenanceRef.from_dict(p) for p in data.get("provenance", ())),
            attributes=data.get("attributes", {}),
        )
