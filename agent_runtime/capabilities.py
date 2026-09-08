"""Capability gates for production reconstruction jobs."""

from __future__ import annotations

from adapters.llm.base import ModelCapabilities


class ReconstructionProfileError(ValueError):
    pass


def require_reconstruction_profile(capabilities: ModelCapabilities) -> None:
    missing = []
    if not capabilities.vision_input:
        missing.append("vision_input")
    if not capabilities.function_tools:
        missing.append("function_tools")
    if not capabilities.structured_output:
        missing.append("structured_output")

    if missing:
        raise ReconstructionProfileError(
            "Selected model is not reconstruction-ready; missing: " + ", ".join(missing)
        )
