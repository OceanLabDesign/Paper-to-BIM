"""planning/llm/claude_cli.py —— 走 Claude Code CLI 的轉接器（不吃 API 金鑰）

**用途**：校對階段讓人在圖上直接問 AI，走的是本機已登入的 Claude Code 訂閱，
`claude -p` 子行程進出，**不需要 ANTHROPIC_API_KEY**。

    LLM_PROVIDER=claude_cli python3 tools/review_ui.py

和 `anthropic.py` 的分工：這支是**校對期的便宜互動**，正式跑迴圈（§11 第 6 步）
仍然走原生 API —— 理由見下面「限制」。

## 圖片怎麼進去

CLI 沒有影像參數，但 Claude Code 自己有 Read 工具、讀得了 PNG。
所以 base.py 的 image 區塊會被**寫成暫存檔**，prompt 裡放路徑，
再用 `--allowed-tools Read` + `--add-dir` 讓它讀得到。暫存檔在 complete() 回來後刪掉。

## 多輪

CLI 每次呼叫是一個新 session。給 `resume=True` 會用上一次的 `session_id`
接續（`--resume`），校對介面靠這個維持「同一段對話」。
`reset()` 開新的一段。

## 限制（為什麼正式迴圈不走這支）

1. **不支援 tool_use 回傳。** `-p` 模式下 CLI 自己把工具跑完才吐最終文字，
   不會把「我想呼叫哪個工具」交還給呼叫端 —— 這跟 base.py 的契約相反，
   也跟 §5「控制權在程式碼」相反。傳 tools 進來會直接擋掉。
   §7.2 的主動工具箱要交給中樞自己調度時，**必須走原生 API**。
2. **每次呼叫有固定開銷**（載入它自己的系統提示與工具定義，實測約 25k token
   的 cache 讀寫），批次跑上百片會比原生 API 貴。
3. 非確定性、且版本跟著本機 CLI 走。**不要拿它產進版控的產物。**
"""

import json
import os
import shutil
import subprocess
import tempfile
from pathlib import Path

from planning.llm.base import Provider

BIN = "claude"
DEFAULT_TIMEOUT = 300          # 秒。看圖＋推理比純文字慢，別設太短
READ_ONLY_TOOLS = "Read"       # 只給讀圖，不讓它動這個 repo 的檔案


class ClaudeCLI(Provider):
    """把 base.py 的訊息格式轉成 `claude -p` 的一次呼叫。

    opts:
        resume    True → 接續上一次的 session（多輪校對用）
        timeout   秒，預設 300
        cwd       子行程的工作目錄，預設是暫存目錄（**刻意不用 repo 根目錄**，
                  免得它載入本專案的 CLAUDE.md 而被無關的指示影響）
    """

    name = "claude_cli"

    def __init__(self, model: str = "", **opts):
        super().__init__(model, **opts)
        self.session_id = ""
        self.last_cost_usd = 0.0

    # ── 主介面 ────────────────────────────────────────────────────────────
    def complete(self, messages, system="", tools=(), max_tokens=4096) -> dict:
        if tools:
            raise NotImplementedError(
                "claude_cli 不支援把 tool_use 交還給呼叫端（見本檔『限制』1）。"
                "要讓中樞自己調度 §7.2 工具箱，請改用 LLM_PROVIDER=anthropic。"
            )
        if not shutil.which(BIN):
            raise RuntimeError(f"找不到 {BIN} 指令；這支轉接器需要本機裝好 Claude Code")

        tmp = Path(tempfile.mkdtemp(prefix="pb_cli_"))
        try:
            prompt = self._flatten(messages, tmp)
            out = self._run(prompt, system, tmp)
        finally:
            shutil.rmtree(tmp, ignore_errors=True)

        if out.get("is_error"):
            raise RuntimeError(f"claude CLI 回錯：{out.get('result', '')[:400]}")

        self.session_id = out.get("session_id", "")
        self.last_cost_usd = out.get("total_cost_usd", 0.0)
        u = out.get("usage", {})
        return {
            "content": [{"type": "text", "text": out.get("result", "")}],
            "stop_reason": "end_turn",
            "usage": {"input_tokens": u.get("input_tokens", 0),
                      "output_tokens": u.get("output_tokens", 0)},
        }

    def reset(self):
        """丟掉 session，下一次 complete() 重新開一段對話。"""
        self.session_id = ""

    # ── 內部 ──────────────────────────────────────────────────────────────
    def _flatten(self, messages: list, tmp: Path) -> str:
        """base.py 的多段訊息 → 一段純文字 prompt；影像落地成檔案。

        CLI 收的是單一 prompt，所以歷史訊息只有在 resume=False 時才需要攤平。
        接續模式下呼叫端通常只傳最後一則。
        """
        parts, n_img = [], 0
        for m in messages:
            who = "使用者" if m.get("role") == "user" else "你先前的回答"
            body = []
            for blk in m.get("content", []):
                t = blk.get("type")
                if t == "text":
                    body.append(blk["text"])
                elif t == "image":
                    n_img += 1
                    ext = blk.get("media_type", "image/png").split("/")[-1]
                    p = tmp / f"img{n_img:02d}.{ext}"
                    p.write_bytes(blk["data"])
                    body.append(f"[圖 {n_img}：{p}]")
                elif t in ("tool_use", "tool_result"):
                    raise NotImplementedError(
                        f"claude_cli 不處理 {t} 區塊（見本檔『限制』1）")
            if body:
                parts.append(f"<{who}>\n" + "\n".join(body) + f"\n</{who}>")

        head = ""
        if n_img:
            head = (f"以下有 {n_img} 張圖，路徑寫在 [圖 N：...] 裡。"
                    "**請先用 Read 工具把每一張都讀進來再回答。**\n\n")
        return head + "\n\n".join(parts)

    def _run(self, prompt: str, system: str, tmp: Path) -> dict:
        cmd = [BIN, "-p", prompt, "--output-format", "json",
               "--allowed-tools", READ_ONLY_TOOLS,
               "--add-dir", str(tmp)]
        if self.model:
            cmd += ["--model", self.model]
        if system:
            cmd += ["--append-system-prompt", system]
        if self.opts.get("resume") and self.session_id:
            cmd += ["--resume", self.session_id]

        r = subprocess.run(
            cmd, capture_output=True, text=True,
            timeout=self.opts.get("timeout", DEFAULT_TIMEOUT),
            cwd=self.opts.get("cwd") or str(tmp),
            env={**os.environ, "CLAUDE_CODE_DISABLE_NONESSENTIAL_TRAFFIC": "1"},
        )
        if r.returncode != 0:
            raise RuntimeError(f"claude CLI 離開碼 {r.returncode}：{r.stderr[:400]}")
        try:
            return json.loads(r.stdout)
        except json.JSONDecodeError:
            raise RuntimeError(f"claude CLI 沒吐出 JSON：{r.stdout[:400]}")
