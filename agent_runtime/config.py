"""Runtime-only configuration for user-selected models and BYOK credentials."""

from __future__ import annotations

from dataclasses import dataclass
import os
from typing import Mapping, Optional


@dataclass(frozen=True)
class AgentModelConfig:
    provider: str
    model_id: str
    api_key: str

    def __post_init__(self) -> None:
        if self.provider != "openrouter":
            raise ValueError(f"Unsupported provider: {self.provider}")
        if not self.model_id.strip():
            raise ValueError("model_id is required")
        if not self.api_key.strip():
            raise ValueError("api_key is required")

    def safe_dict(self) -> dict[str, str]:
        """Serializable view that intentionally excludes credentials."""
        return {"provider": self.provider, "model_id": self.model_id}

    @classmethod
    def from_environment(
        cls,
        *,
        model_id: Optional[str] = None,
        environ: Optional[Mapping[str, str]] = None,
    ) -> "AgentModelConfig":
        env = os.environ if environ is None else environ
        selected_model = model_id or env.get("PAPER_TO_BIM_MODEL") or env.get("OPENROUTER_MODEL")
        api_key = env.get("OPENROUTER_API_KEY")
        if not selected_model:
            raise ValueError("No OpenRouter model selected")
        if not api_key:
            raise ValueError("OPENROUTER_API_KEY is not set")
        return cls(provider="openrouter", model_id=selected_model, api_key=api_key)
