"""s05_solve —— 尺寸鏈求解

規格：v0.4 §2、§3、§7.1、裁決 §5
輸入：{case}/04_readings.csv
輸出：{case}/05_chains.csv、{case}/05_chain_members.csv
      ＋ **append 到 {case}/08_conflicts.csv，`source` 欄填 `chain_closure`**（裁決 §5）

要點：
  - **尺寸是幾何，線段只是拓樸；座標只來自數字與量測。**
  - 鏈要帶閉合狀態 —— 全部的 chains（含閉合狀態）會整包進中樞脈絡（§7.1）
  - 閉合對不起來就**當場**寫進 08_conflicts.csv，不要平均、不要硬湊、也不要留到最後統一收集
    （裁決 §5：conflicts 是逐步發現的，回頭重讀所有版本複雜且容易漏）

迴歸測試：68 年案 **403 + 403 = 806**（§11 第 4 步的第一筆）。
"""

from pathlib import Path

from core.fields import CONFLICT_SOURCES

CONFLICT_SOURCE = CONFLICT_SOURCES[0]   # "chain_closure"（裁決 §5）


def run(case_dir: Path) -> None:
    raise NotImplementedError("s05_solve 未實作（§11 第 4 步）")
