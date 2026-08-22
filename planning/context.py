"""planning/context.py —— §7.1 脈絡節食

中樞收到的是**摘要，不是原始資料**：
  - 02_sheets 該張圖整列、品質地圖摘要（差區清單）、排除帶
  - 05_chains 全部（含閉合狀態）
  - 03_elements **統計＋高信心清單**（低信心的只給數量，要看自己呼叫工具）
  - 上一輪 residuals（v2 起）

§12 紅線：**不要把 649 條線段原始資料塞進中樞脈絡** —— 給摘要，細節靠工具（§7.2）。
"""

from pathlib import Path


def build_context(case_dir, sheet_id, residuals=None) -> dict:
    raise NotImplementedError("build_context 未實作（§11 第 6 步）")
