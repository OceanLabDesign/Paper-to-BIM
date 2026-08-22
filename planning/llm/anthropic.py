"""planning/llm/anthropic.py —— Anthropic 原生轉接器

§11 第 6 步「接真中樞（Claude API）」走這支。

金鑰從環境變數 ANTHROPIC_API_KEY 取，**不要寫進 core/config.py**
（那支是實測校準參數，而且會進版控）。
"""

import os

from planning.llm.base import Provider

ENV_KEY = "ANTHROPIC_API_KEY"


class Anthropic(Provider):
    name = "anthropic"

    def complete(self, messages, system="", tools=(), max_tokens=4096) -> dict:
        raise NotImplementedError(
            "Anthropic 轉接器未實作（§11 第 6 步）。"
            f"實作時：讀 {ENV_KEY}、把 base.py 的 image 區塊轉成 base64 source、"
            "把 TOOL_SPECS 的 parameters 放進 input_schema。"
        )
