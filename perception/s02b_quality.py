"""s02b_quality —— 品質地圖

規格：v0.4 §8（v0.4 新增的被動層三支之一）
輸入：{case}/01_tiles_upright/*.png（**轉正後** —— 品質分區要跟下游同一個座標系）
輸出：{case}/02_quality.csv

要點：每 256px 區塊算對比度、雜訊、筆畫密度 → 分級 good / shadow / crease / bleed。
      **純統計，無 AI。**

下游：03_elements 的 quality_zone 欄（§9）、中樞脈絡的「差區清單」（§7.1）、
      s08 殘差落在 crease 區者自動註記（§8）。
"""

from pathlib import Path

QUALITY_LEVELS = ("good", "shadow", "crease", "bleed")  # §8
BLOCK_PX = 256                                          # §8


def run(case_dir: Path) -> None:
    raise NotImplementedError("s02b_quality 未實作（§11 第 3 步）")
