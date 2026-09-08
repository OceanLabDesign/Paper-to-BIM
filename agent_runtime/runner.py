"""Bounded model/tool loop for reconstruction reasoning.

The runtime controls iteration and tool-call limits. Models may choose tools but
cannot extend the loop, bypass validation, or write CAD directly.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any, Mapping, Sequence
from uuid import uuid4

from adapters.llm.base import ModelProvider, ModelRequest
from .capabilities import require_reconstruction_profile
from .records import ToolCallRecord
from .tools import ToolRegistry


@dataclass(frozen=True)
class AgentLimits:
    max_iterations: int = 6
    max_tool_calls: int = 24
    max_schema_retries: int = 2


@dataclass(frozen=True)
class AgentRunResult:
    content: Any
    records: tuple[ToolCallRecord, ...]
    iterations: int
    tool_calls: int


class AgentRuntime:
    def __init__(
        self,
        *,
        provider: ModelProvider,
        model_id: str,
        tools: ToolRegistry,
        limits: AgentLimits = AgentLimits(),
    ) -> None:
        require_reconstruction_profile(provider.capabilities(model_id))
        self.provider = provider
        self.model_id = model_id
        self.tools = tools
        self.limits = limits

    def run(
        self,
        *,
        messages: Sequence[Mapping[str, Any]],
        response_schema: Mapping[str, Any] | None = None,
    ) -> AgentRunResult:
        transcript: list[Mapping[str, Any]] = list(messages)
        records: list[ToolCallRecord] = []
        total_tool_calls = 0
        last_content: Any = None

        for iteration in range(1, self.limits.max_iterations + 1):
            response = self.provider.complete(
                ModelRequest(
                    model_id=self.model_id,
                    messages=tuple(transcript),
                    tools=self.tools.model_tools(),
                    response_schema=response_schema,
                    tool_choice="auto",
                )
            )
            last_content = response.content

            assistant_message: dict[str, Any] = {"role": "assistant", "content": response.content}
            if response.tool_calls:
                assistant_message["tool_calls"] = list(response.tool_calls)
            transcript.append(assistant_message)

            if not response.tool_calls:
                return AgentRunResult(
                    content=last_content,
                    records=tuple(records),
                    iterations=iteration,
                    tool_calls=total_tool_calls,
                )

            for call in response.tool_calls:
                if total_tool_calls >= self.limits.max_tool_calls:
                    raise RuntimeError("Agent tool-call limit reached")

                call_id = str(call.get("id") or uuid4())
                function = call.get("function", {}) or {}
                tool_name = str(function.get("name") or "")
                raw_args = function.get("arguments", {})
                if isinstance(raw_args, str):
                    try:
                        arguments = json.loads(raw_args)
                    except json.JSONDecodeError as exc:
                        raise RuntimeError(f"Invalid JSON arguments for tool {tool_name}") from exc
                else:
                    arguments = dict(raw_args or {})

                result = self.tools.execute(tool_name, arguments)
                total_tool_calls += 1
                records.append(
                    ToolCallRecord.create(
                        call_id=call_id,
                        tool_name=tool_name,
                        arguments=arguments,
                        model_id=self.model_id,
                        iteration=iteration,
                        result_refs=result.result_refs,
                    )
                )

                transcript.append(
                    {
                        "role": "tool",
                        "tool_call_id": call_id,
                        "name": tool_name,
                        "content": json.dumps(result.content, ensure_ascii=False),
                    }
                )

        raise RuntimeError("Agent iteration limit reached before completion")
