"""Compatibility adapter from legacy ``plan_vN`` mappings to ``DrawingIR``.

This is intentionally conservative.  It preserves legacy judgments as inferred
entities but does not pretend that old plan geometry has already passed through
new constraint solving.  The adapter exists so exporters can migrate before the
entire upstream pipeline is rewritten.
"""

from __future__ import annotations

from typing import Any, Mapping

from domain import DrawingIR, Entity, EntityState, ProvenanceRef


LEGACY_ENTITY_TYPE_MAP = {
    "wall": "building.wall",
    "column": "building.column",
    "opening": "building.opening",
    "door": "building.door",
    "window": "building.window",
    "stair": "building.stair",
    "dim_line": "annotation.dimension_line",
    "dim_text": "annotation.dimension_text",
    "level_line": "annotation.level_line",
    "level_text": "annotation.level_text",
    "room_label": "annotation.room_label",
    "material_note": "annotation.material_note",
    "calc_note": "annotation.calc_note",
}


def plan_to_drawing_ir(plan: Mapping[str, Any]) -> DrawingIR:
    """Convert one validated legacy plan into a compatibility DrawingIR.

    This adapter is not a replacement for reconstruction/solver.  Entities are
    marked ``INFERRED`` and carry provenance back to the legacy plan judgment.
    Unknown legacy types are retained under ``legacy.<type>`` rather than dropped.
    """

    meta = plan.get("meta", {}) or {}
    context = plan.get("context", {}) or {}
    version = meta.get("version")

    entities = []
    for index, judgment in enumerate(plan.get("judgments", ()) or ()):
        judgment_id = str(judgment.get("id") or f"judgment-{index + 1}")
        legacy_type = str(judgment.get("type") or "unknown")
        entity_type = LEGACY_ENTITY_TYPE_MAP.get(legacy_type, f"legacy.{legacy_type}")
        confidence = float(judgment.get("confidence", 0.5))
        confidence = min(1.0, max(0.0, confidence))

        provenance = (
            ProvenanceRef(
                source_kind="legacy_plan",
                source_id=judgment_id,
                sheet_id=str(meta.get("sheet")) if meta.get("sheet") is not None else None,
                method=f"plan_v{version}" if version is not None else "legacy_plan",
            ),
        )

        attributes = {
            "legacy_type": legacy_type,
            "legacy_evidence": list(judgment.get("evidence", ()) or ()),
            "legacy_note": judgment.get("note"),
        }

        entities.append(
            Entity(
                id=judgment_id,
                type=entity_type,
                geometry=dict(judgment.get("geometry", {}) or {}),
                confidence=confidence,
                state=EntityState.INFERRED,
                provenance=provenance,
                attributes=attributes,
            )
        )

    return DrawingIR(
        entities=tuple(entities),
        metadata={
            "source": "legacy_plan",
            "legacy_meta": dict(meta),
            "legacy_context": dict(context),
        },
    )
