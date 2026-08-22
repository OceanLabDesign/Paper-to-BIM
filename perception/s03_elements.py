"""s03_elements —— 富標籤

規格：v0.4 §8、§9
輸入：03_lines ＋ 03_detections ＋ 03_texts ＋ 02_quality ＋ 02_exclude
順序：排在 s03_lines → s03_detect → s03_texts 之後（裁決 §2）
輸出：{case}/03_elements.csv

要點：**排除帶內的線先剔**；每筆標籤附品質區（quality_zone）。
      §9 欄位：conf, evidence, provenance, quality_zone, status
      本層一律寫 status=`proposed`；改成 adopted/rejected/uncertain 是中樞在 plan 裡
      裁定、由 orchestrator 回寫的事（§9），**這支不准自己改**。
"""

from pathlib import Path


def run(case_dir: Path) -> None:
    raise NotImplementedError("s03_elements 未實作（§11 第 3 步）")
