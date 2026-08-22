"""perception/detectors/rule.py —— 規則式偵測器（第一版）

規格：裁決 §2。s03_detect 的第一版偵測器 —— **是規則，不是 YOLO**。
輸入：03_lines.csv 的線段
輸出：候選框，寫進 03_detections.csv，`detector` 欄填 `rule_v1`

三條規則（從線段反推候選框）：
  平行線對          → wall     （間距落在 core.config.WALL_GAP_PX 內）
  實心矩形          → column
  線 + 兩端斜線     → dim_line

類別一律引 core/classes.py（順序即 id）。輸出是 §9 富標籤，status 一律 `proposed`。
"""

from pathlib import Path

DETECTOR_ID = "rule_v1"  # 裁決 §2：寫進 03_detections 的 detector 欄


def detect(lines) -> list:
    raise NotImplementedError("rule_v1 偵測器未實作（§11 第 3 步）")
