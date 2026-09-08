"""Provider-neutral contracts for multimodal agent models."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Mapping, Optional, Sequence


@dataclass(frozen=True)
class ModelCapabilities:
    vision_input: bool = False
    structured_output: bool = False
    function_tools: bool = False
    pdf_input: bool = False
    reasoning: bool = False
    context_length: Optional[int] = None

    @property
    def reconstruction_ready(self) -> bool:
        return self.vision_input and self.structured_output and self.function_tools


@dataclass(frozen=True)
class ModelRequest:
    model_id: str
    messages: Sequence[Mapping[str, Any]]
    tools: Sequence[Mapping[str, Any]] = field(default_factory=tuple)
    response_schema: Optional[Mapping[str, Any]] = None
    tool_choice: Any = None
    temperature: Optional[float] = None
    max_tokens: Optional[int] = None
    extra: Mapping[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class ModelResponse:
    model_id: str
    content: Any
    tool_calls: Sequence[Mapping[str, Any]] = field(default_factory=tuple)
    raw: Mapping[str, Any] = field(default_factory=dict)


class ModelProvider:
    """Minimal provider interface used by the agent runtime."""

    def capabilities(self, model_id: str) -> ModelCapabilities:
        raise NotImplementedError

    def complete(self, request: ModelRequest) -> ModelResponse:
        raise NotImplementedError
