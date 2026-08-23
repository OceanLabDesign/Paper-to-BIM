"""planning/llm/registry.py —— 依設定選供應商

用法：
    from planning.llm.registry import get_provider
    llm = get_provider()                        # 讀環境變數
    llm = get_provider("ollama", model="qwen2.5-vl")

環境變數：
    LLM_PROVIDER   anthropic（預設）| openai | ollama | vllm | lmstudio
                   | claude_cli（走本機 Claude Code 訂閱，免金鑰；限制見該檔）
    LLM_MODEL      模型 id
    LLM_BASE_URL   覆寫 OpenAI 相容端點的網址

新增廠商＝在 PROVIDERS 加一列，中樞完全不動。
"""

import os

from planning.llm.anthropic import Anthropic
from planning.llm.claude_cli import ClaudeCLI
from planning.llm.openai_compat import OpenAICompat, LOCAL_BASE_URLS

# 名稱 → (類別, 預設 kwargs)
PROVIDERS = {
    "anthropic": (Anthropic, {}),
    "openai": (OpenAICompat, {}),
    "ollama": (OpenAICompat, {"base_url": LOCAL_BASE_URLS["ollama"]}),
    "vllm": (OpenAICompat, {"base_url": LOCAL_BASE_URLS["vllm"]}),
    "lmstudio": (OpenAICompat, {"base_url": LOCAL_BASE_URLS["lmstudio"]}),
    # 走本機已登入的 Claude Code，不吃 API 金鑰。校對期互動用，不跑正式迴圈
    "claude_cli": (ClaudeCLI, {}),
}

DEFAULT_PROVIDER = "anthropic"
DEFAULT_MODELS = {"anthropic": "claude-opus-5", "openai": "gpt-5",
                  "claude_cli": ""}          # 空字串＝用 CLI 目前的預設模型


def get_provider(name: str = "", model: str = "", **opts):
    name = name or os.environ.get("LLM_PROVIDER", DEFAULT_PROVIDER)
    if name not in PROVIDERS:
        raise KeyError(f"未知的供應商 {name!r}；可用：{sorted(PROVIDERS)}")
    cls, defaults = PROVIDERS[name]
    model = model or os.environ.get("LLM_MODEL") or DEFAULT_MODELS.get(name, "")
    if not model and name not in ("claude_cli",):   # 這支可以不指定模型
        raise ValueError(f"供應商 {name!r} 沒有預設模型，請給 model 或設 LLM_MODEL")
    return cls(model, **{**defaults, **opts})
