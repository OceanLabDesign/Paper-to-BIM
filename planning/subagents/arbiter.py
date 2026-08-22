"""讀數仲裁 sub-agent

規格：v0.4 §7.4
入：一張小圖 ＋ 三源值 ＋ 品質區資訊
出：{裁定值 | null, 信心, 一句理由}      ← 裁不出來就回 null，不要硬選一個

可用本地小模型。**只給建議，不做定案**：產出經中樞進 plan、經 validate 才算數。
"""

from pathlib import Path


def arbitrate(crop, readings, quality_zone) -> dict:
    raise NotImplementedError("讀數仲裁未實作（§11 第 6 步）")
