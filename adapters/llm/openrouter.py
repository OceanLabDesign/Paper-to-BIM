"""OpenRouter BYOK adapter for the Paper-to-BIM agent runtime.

The API key is accepted only at runtime and is never serialized by this module.
"""

from __future__ import annotations

import json
import urllib.error
import urllib.request
from dataclasses import dataclass
from typing import Any, Mapping, Optional

from .base import ModelCapabilities, ModelProvider, ModelRequest, ModelResponse


OPENROUTER_BASE_URL = "https://openrouter.ai/api/v1"


@dataclass(frozen=True)
class OpenRouterConfig:
    api_key: str
    base_url: str = OPENROUTER_BASE_URL
    app_url: Optional[str] = None
    app_title: str = "Paper-to-BIM"
    timeout_seconds: float = 120.0

    def __post_init__(self) -> None:
        if not self.api_key or not self.api_key.strip():
            raise ValueError("OpenRouter API key is required")


class OpenRouterProvider(ModelProvider):
    """Small OpenAI-compatible OpenRouter client using only Python stdlib.

    Keeping the adapter dependency-free avoids forcing an HTTP SDK into the
    canonical domain. A richer transport can replace this class later without
    changing agent or reconstruction contracts.
    """

    def __init__(self, config: OpenRouterConfig) -> None:
        self._config = config
        self._models_cache: Optional[dict[str, Mapping[str, Any]]] = None

    def _headers(self) -> dict[str, str]:
        headers = {
            "Authorization": f"Bearer {self._config.api_key}",
            "Content-Type": "application/json",
            "X-Title": self._config.app_title,
        }
        if self._config.app_url:
            headers["HTTP-Referer"] = self._config.app_url
        return headers

    def _request_json(self, method: str, path: str, payload: Optional[Mapping[str, Any]] = None) -> Mapping[str, Any]:
        body = None if payload is None else json.dumps(payload).encode("utf-8")
        request = urllib.request.Request(
            f"{self._config.base_url.rstrip('/')}/{path.lstrip('/')}",
            data=body,
            headers=self._headers(),
            method=method,
        )
        try:
            with urllib.request.urlopen(request, timeout=self._config.timeout_seconds) as response:
                return json.loads(response.read().decode("utf-8"))
        except urllib.error.HTTPError as exc:
            detail = exc.read().decode("utf-8", errors="replace")
            raise RuntimeError(f"OpenRouter HTTP {exc.code}: {detail}") from exc
        except urllib.error.URLError as exc:
            raise RuntimeError(f"OpenRouter request failed: {exc.reason}") from exc

    def list_models(self, *, refresh: bool = False) -> tuple[Mapping[str, Any], ...]:
        if self._models_cache is None or refresh:
            response = self._request_json("GET", "/models")
            models = response.get("data", ())
            self._models_cache = {str(model["id"]): model for model in models if "id" in model}
        return tuple(self._models_cache.values())

    def model_info(self, model_id: str) -> Mapping[str, Any]:
        if self._models_cache is None:
            self.list_models()
        assert self._models_cache is not None
        try:
            return self._models_cache[model_id]
        except KeyError as exc:
            raise KeyError(f"OpenRouter model not found: {model_id}") from exc

    def capabilities(self, model_id: str) -> ModelCapabilities:
        """Infer reconstruction capabilities from OpenRouter model metadata.

        OpenRouter model metadata can evolve, so unknown capability fields are
        treated conservatively as unsupported. The UI may still let a user pick
        such a model, but production reconstruction must pass the capability gate.
        """
        model = self.model_info(model_id)
        architecture = model.get("architecture", {}) or {}
        input_modalities = set(architecture.get("input_modalities", ()) or ())
        supported = set(model.get("supported_parameters", ()) or ())

        context_length = model.get("context_length")
        try:
            context_length = int(context_length) if context_length is not None else None
        except (TypeError, ValueError):
            context_length = None

        return ModelCapabilities(
            vision_input="image" in input_modalities,
            pdf_input="file" in input_modalities or "pdf" in input_modalities,
            function_tools="tools" in supported or "tool_choice" in supported,
            structured_output="response_format" in supported,
            reasoning="reasoning" in supported,
            context_length=context_length,
        )

    def complete(self, request: ModelRequest) -> ModelResponse:
        payload: dict[str, Any] = {
            "model": request.model_id,
            "messages": list(request.messages),
        }
        if request.tools:
            payload["tools"] = list(request.tools)
        if request.tool_choice is not None:
            payload["tool_choice"] = request.tool_choice
        if request.response_schema is not None:
            payload["response_format"] = {
                "type": "json_schema",
                "json_schema": request.response_schema,
            }
        if request.temperature is not None:
            payload["temperature"] = request.temperature
        if request.max_tokens is not None:
            payload["max_tokens"] = request.max_tokens
        payload.update(dict(request.extra))

        raw = self._request_json("POST", "/chat/completions", payload)
        choices = raw.get("choices", ())
        if not choices:
            raise RuntimeError("OpenRouter returned no choices")

        message = choices[0].get("message", {}) or {}
        return ModelResponse(
            model_id=str(raw.get("model") or request.model_id),
            content=message.get("content"),
            tool_calls=tuple(message.get("tool_calls", ()) or ()),
            raw=raw,
        )
