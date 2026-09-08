from adapters.llm.base import ModelCapabilities
from agent_runtime.capabilities import ReconstructionProfileError, require_reconstruction_profile
from agent_runtime.config import AgentModelConfig
from agent_runtime.records import arguments_hash
from agent_runtime.tools import ToolRegistry
from agent_tools import make_grid_solver_tool


def test_byok_safe_dict_never_contains_api_key():
    config = AgentModelConfig(provider="openrouter", model_id="vendor/model", api_key="super-secret")
    assert config.safe_dict() == {"provider": "openrouter", "model_id": "vendor/model"}
    assert "super-secret" not in repr(config.safe_dict())


def test_reconstruction_profile_requires_vision_tools_and_schema():
    require_reconstruction_profile(
        ModelCapabilities(vision_input=True, function_tools=True, structured_output=True)
    )

    try:
        require_reconstruction_profile(
            ModelCapabilities(vision_input=True, function_tools=False, structured_output=True)
        )
    except ReconstructionProfileError as exc:
        assert "function_tools" in str(exc)
    else:
        raise AssertionError("tool-less model must be rejected")


def test_tool_audit_hash_redacts_common_secret_fields():
    a = arguments_hash({"api_key": "first", "value": 3})
    b = arguments_hash({"api_key": "second", "value": 3})
    assert a == b


def test_grid_solver_tool_returns_mm_coordinates_and_conflicts():
    registry = ToolRegistry()
    registry.register(make_grid_solver_tool())

    result = registry.execute(
        "solve_grid_coordinates",
        {
            "origin_axis": "A",
            "distances": [
                {"start": "A", "end": "B", "distance_mm": 6000, "constraint_id": "ab"},
                {"start": "B", "end": "C", "distance_mm": 4500, "constraint_id": "bc"},
                {"start": "A", "end": "C", "distance_mm": 10500, "constraint_id": "ac"},
            ],
        },
    )

    assert result.content["unit"] == "mm"
    assert result.content["positions"]["C"] == 10500.0
    assert result.content["solved"] is True
