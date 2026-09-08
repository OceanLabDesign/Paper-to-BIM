"""Provenance primitives for traceable reconstruction decisions."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping, Optional, Tuple


BBox = Tuple[float, float, float, float]


@dataclass(frozen=True)
class ProvenanceRef:
    """Reference from a domain object back to its supporting evidence.

    `source_kind` is a stable namespace such as ``image_region``, ``ocr_reading``,
    ``legacy_csv``, ``human_review`` or ``solver``.  The domain layer deliberately
    does not know how those sources are stored.
    """

    source_kind: str
    source_id: str
    sheet_id: Optional[str] = None
    page: Optional[int] = None
    bbox: Optional[BBox] = None
    method: Optional[str] = None
    actor: Optional[str] = None
    model: Optional[str] = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "source_kind": self.source_kind,
            "source_id": self.source_id,
            "sheet_id": self.sheet_id,
            "page": self.page,
            "bbox": list(self.bbox) if self.bbox is not None else None,
            "method": self.method,
            "actor": self.actor,
            "model": self.model,
        }

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> "ProvenanceRef":
        bbox = data.get("bbox")
        return cls(
            source_kind=str(data["source_kind"]),
            source_id=str(data["source_id"]),
            sheet_id=data.get("sheet_id"),
            page=data.get("page"),
            bbox=tuple(float(v) for v in bbox) if bbox is not None else None,
            method=data.get("method"),
            actor=data.get("actor"),
            model=data.get("model"),
        )
