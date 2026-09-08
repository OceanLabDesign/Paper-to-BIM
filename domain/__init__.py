"""Canonical domain model for Paper-to-BIM reconstruction.

This package is intentionally dependency-light: no LLM SDK, OpenCV,
ezdxf, MCP, or UI dependencies belong here.
"""

from .observation import Observation
from .constraint import Constraint, ConstraintStrength
from .entity import Entity, EntityState
from .conflict import Conflict, ConflictStatus
from .provenance import ProvenanceRef
from .drawing_ir import DrawingIR

__all__ = [
    "Observation",
    "Constraint",
    "ConstraintStrength",
    "Entity",
    "EntityState",
    "Conflict",
    "ConflictStatus",
    "ProvenanceRef",
    "DrawingIR",
]
