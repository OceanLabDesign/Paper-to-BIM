"""Semantic tool registry exposed to reconstruction agents."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable, Mapping, Optional


@dataclass(frozen=True)
class ToolResult:
    content: Any
    result_refs: tuple[str, ...] = ()


@dataclass(frozen=True)
class ToolDefinition:
    name: str
    description: str
    input_schema: Mapping[str, Any]
    handler: Callable[[Mapping[str, Any]], ToolResult]
    category: str
    mutates_domain: bool = False

    def as_model_tool(self) -> dict[str, Any]:
        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": self.description,
                "parameters": dict(self.input_schema),
            },
        }


class ToolRegistry:
    ALLOWED_CATEGORIES = {"inspection", "measurement", "reconstruction", "solver", "review"}

    def __init__(self) -> None:
        self._tools: dict[str, ToolDefinition] = {}

    def register(self, tool: ToolDefinition) -> None:
        if tool.category not in self.ALLOWED_CATEGORIES:
            raise ValueError(f"Unsupported tool category: {tool.category}")
        if tool.name in self._tools:
            raise ValueError(f"Duplicate tool: {tool.name}")
        self._tools[tool.name] = tool

    def get(self, name: str) -> ToolDefinition:
        try:
            return self._tools[name]
        except KeyError as exc:
            raise KeyError(f"Unknown agent tool: {name}") from exc

    def execute(self, name: str, arguments: Mapping[str, Any]) -> ToolResult:
        return self.get(name).handler(arguments)

    def model_tools(self, *, category: Optional[str] = None) -> tuple[dict[str, Any], ...]:
        tools = self._tools.values()
        if category is not None:
            tools = (tool for tool in tools if tool.category == category)
        return tuple(tool.as_model_tool() for tool in tools)

    def names(self) -> tuple[str, ...]:
        return tuple(self._tools)
