from domain import (
    Conflict,
    Constraint,
    ConstraintStrength,
    DrawingIR,
    Entity,
    EntityState,
    Observation,
    ProvenanceRef,
)


def build_ir() -> DrawingIR:
    source = ProvenanceRef(
        source_kind="image_region",
        source_id="p03-r2",
        sheet_id="sheet-p03",
        page=3,
        bbox=(0.10, 0.20, 0.30, 0.40),
        method="vision",
        model="test-model",
    )

    dim = Observation(
        id="obs-dim-ab",
        type="annotation.dimension_text",
        confidence=0.98,
        value=6000,
        unit="mm",
        provenance=(source,),
    )

    distance = Constraint(
        id="constraint-ab",
        type="distance",
        targets=("drawing.grid_axis:A", "drawing.grid_axis:B"),
        strength=ConstraintStrength.HARD,
        confidence=0.98,
        value=6000,
        unit="mm",
        provenance=(source,),
    )

    column = Entity(
        id="column-C1-01",
        type="building.column",
        geometry={"center": [6000, 3000], "width": 600, "depth": 600},
        confidence=0.96,
        state=EntityState.CONFIRMED,
        provenance=(source,),
        attributes={"tag": "C1"},
    )

    conflict = Conflict(
        id="conflict-chain-01",
        kind="chain_closure",
        description="Local chain and total dimension disagree by 200 mm",
        involved_ids=("constraint-ab", "obs-total"),
    )

    return DrawingIR(
        observations=(dim,),
        constraints=(distance,),
        entities=(column,),
        conflicts=(conflict,),
        metadata={"sheet_id": "sheet-p03"},
    )


def test_json_round_trip_is_lossless():
    original = build_ir()
    restored = DrawingIR.from_json(original.to_json())
    assert restored == original


def test_json_serialization_is_deterministic():
    ir = build_ir()
    assert ir.to_json() == ir.to_json()


def test_unresolved_conflict_is_valid_output():
    restored = DrawingIR.from_json(build_ir().to_json())
    assert len(restored.conflicts) == 1
    assert restored.conflicts[0].status.value == "open"


def test_confidence_bounds_are_enforced():
    try:
        Observation(id="bad", type="annotation.dimension_text", confidence=1.2)
    except ValueError as exc:
        assert "confidence" in str(exc)
    else:
        raise AssertionError("confidence > 1 must be rejected")
