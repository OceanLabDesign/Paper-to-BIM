from adapters.legacy_plan import plan_to_drawing_ir


def test_legacy_plan_becomes_inferred_drawing_ir():
    plan = {
        "meta": {"sheet": "p03", "version": 2},
        "context": {"unit": "cm", "kind": "plan"},
        "judgments": [
            {
                "id": "j-column-1",
                "type": "column",
                "geometry": {"outline_wkt": "POLYGON((0 0,60 0,60 60,0 60,0 0))"},
                "evidence": ["chain#c003"],
                "confidence": 0.9,
            }
        ],
    }

    ir = plan_to_drawing_ir(plan)

    assert len(ir.entities) == 1
    entity = ir.entities[0]
    assert entity.type == "building.column"
    assert entity.state.value == "inferred"
    assert entity.provenance[0].source_kind == "legacy_plan"
    assert entity.attributes["legacy_evidence"] == ["chain#c003"]
