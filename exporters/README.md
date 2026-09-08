# Exporter boundary

New exporter work should consume `domain.DrawingIR` as the canonical input.

Legacy `plan_vN` compatibility is handled outside this package through
`adapters.legacy_plan.plan_to_drawing_ir()`.

The existing `execution/exporters/` package remains in place during migration.
It will be moved behind this boundary incrementally rather than rewritten in one step.
