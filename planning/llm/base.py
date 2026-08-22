"""planning/llm/base.py —— LLM 供應商介面

中樞（planning/proposer.py）只認這個介面，**不認任何廠商 SDK**。
換供應商＝換一個轉接器，中樞、工具、prompt 全不動。

資料一律用 dict（v0.3 原則：程式用 dict 不用 dataclass）。

訊息
    {"role": "user" | "assistant", "content": [區塊, ...]}
    system prompt 另外用 complete() 的 system 參數傳，不放進 messages
    （Anthropic 與 OpenAI 對 system 的處理不同，由轉接器各自吸收）

內容區塊
    {"type": "text",        "text": str}
    {"type": "image",       "media_type": "image/png", "data": bytes}
        ← 多模態：crop_look / compare_floors 讓中樞親眼看圖（§7.2）
    {"type": "tool_use",    "id": str, "name": str, "input": dict}
    {"type": "tool_result", "tool_use_id": str, "content": [區塊, ...]}

回應
    {"content": [區塊, ...],
     "stop_reason": "end_turn" | "tool_use" | "max_tokens",
     "usage": {"input_tokens": int, "output_tokens": int}}

工具規格
    planning/tools.py 的 TOOL_SPECS，形如
    {"name": str, "description": str, "parameters": {JSON Schema}}
    轉接器負責把它轉成該廠商的格式。
"""

BLOCK_TYPES = ("text", "image", "tool_use", "tool_result")
STOP_REASONS = ("end_turn", "tool_use", "max_tokens")


class Provider:
    """供應商轉接器的基底。子類只需實作 complete()。

    name    給 registry 與 log 用的識別字串
    model   實際要呼叫的模型 id
    """

    name = "base"

    def __init__(self, model: str, **opts):
        self.model = model
        self.opts = opts

    def complete(self, messages: list, system: str = "",
                 tools: tuple = (), max_tokens: int = 4096) -> dict:
        """送出一輪對話，回傳上面定義的回應 dict。

        **同步、單輪。** 迴圈控制權在 planning/orchestrator.py（§5 鐵則），
        這支不准自己重試到滿意、不准自己決定要不要再問一次。
        工具的實際執行也不在這裡 —— 這支只回報「模型想呼叫哪個工具」，
        真的去跑是中樞的事。
        """
        raise NotImplementedError(f"{type(self).__name__}.complete 未實作")


def text(s: str) -> dict:
    return {"type": "text", "text": s}


def image(data: bytes, media_type: str = "image/png") -> dict:
    return {"type": "image", "media_type": media_type, "data": data}


def user(*blocks) -> dict:
    return {"role": "user", "content": list(blocks)}


def assistant(*blocks) -> dict:
    return {"role": "assistant", "content": list(blocks)}
