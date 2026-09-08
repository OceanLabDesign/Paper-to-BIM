"""Audit records for agent tool execution."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from hashlib import sha256
import json
from typing import Any, Mapping, Tuple


_SECRET_KEYS = {"api_key", "authorization", "token", "secret", "password"}


def _redact(value: Any) -> Any:
    if isinstance(value, Mapping):
        return {
            str(k): ("[REDACTED]" if str(k).lower() in _SECRET_KEYS else _redact(v))
            for k, v in value.items()
        }
    if isinstance(value, (list, tuple)):
        return [_redact(v) for v in value]
    return value


def arguments_hash(arguments: Mapping[str, Any]) -> str:
    safe = _redact(arguments)
    payload = json.dumps(safe, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return sha256(payload.encode("utf-8")).hexdigest()


@dataclass(frozen=True)
class ToolCallRecord:
    call_id: str
    tool_name: str
    arguments_hash: str
    model_id: str
    iteration: int
    result_refs: Tuple[str, ...] = field(default_factory=tuple)
    timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    @classmethod
    def create(
        cls,
        *,
        call_id: str,
        tool_name: str,
        arguments: Mapping[str, Any],
        model_id: str,
        iteration: int,
        result_refs: tuple[str, ...] = (),
    ) -> "ToolCallRecord":
        return cls(
            call_id=call_id,
            tool_name=tool_name,
            arguments_hash=arguments_hash(arguments),
            model_id=model_id,
            iteration=iteration,
            result_refs=result_refs,
        )
