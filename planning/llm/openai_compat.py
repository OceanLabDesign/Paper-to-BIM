"""planning/llm/openai_compat.py —— OpenAI 相容端點轉接器

**一支涵蓋多個來源** —— 它們都提供 /v1/chat/completions 相容介面：
    OpenAI、Ollama、vLLM、LM Studio、llama.cpp server、以及多數本地多模態部署。

差別只在 base_url 與金鑰：
    OpenAI      https://api.openai.com/v1        需要 OPENAI_API_KEY
    Ollama      http://localhost:11434/v1        金鑰隨便填
    vLLM        http://localhost:8000/v1         金鑰隨便填
    LM Studio   http://localhost:1234/v1         金鑰隨便填

本地部署是「不確定往上傳不往下傳」的實際保障之一：
掃描圖含個資與著作權，跑本地模型時圖不出機器。
"""

import os

from planning.llm.base import Provider

ENV_KEY = "OPENAI_API_KEY"
ENV_BASE_URL = "LLM_BASE_URL"
LOCAL_BASE_URLS = {
    "ollama": "http://localhost:11434/v1",
    "vllm": "http://localhost:8000/v1",
    "lmstudio": "http://localhost:1234/v1",
}


class OpenAICompat(Provider):
    name = "openai_compat"

    def __init__(self, model: str, base_url: str = "", **opts):
        super().__init__(model, **opts)
        self.base_url = base_url or os.environ.get(ENV_BASE_URL, "https://api.openai.com/v1")

    def complete(self, messages, system="", tools=(), max_tokens=4096) -> dict:
        raise NotImplementedError(
            "OpenAI 相容轉接器未實作（§11 第 6 步）。"
            "實作時：system 併成 messages[0] 的 role=system、"
            "image 區塊轉成 data: URL 放進 content 的 image_url、"
            "TOOL_SPECS 包成 {'type':'function','function':{…}}。"
        )
