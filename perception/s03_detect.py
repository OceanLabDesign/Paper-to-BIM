"""s03_detect —— 元件偵測

規格：裁決 §2（v0.4 §8 漏了這支，v0.4.1 補上）
輸入：{case}/03_lines.csv
輸出：{case}/03_detections.csv

**第一版偵測器是規則式，不是 YOLO** —— 實作在 perception/detectors/rule.py，
從線段反推候選框：平行線對→wall、實心矩形→column、線+兩端斜線→dim_line。
`detector` 欄填 `rule_v1`。detectors/yolo.py 是空殼（§12：等存量配對盤點的數字）。

輸出是 §9 富標籤：..., conf, evidence, provenance, quality_zone, status
本層寫出來的 status 一律是 `proposed` —— **標籤是主張，不是事實**。
類別一律引 core/classes.py（順序即 id）。
"""

from pathlib import Path

from perception.detectors import rule


def run(case_dir: Path) -> None:
    raise NotImplementedError("s03_detect 未實作（§11 第 3 步）；偵測器見 detectors/rule.py")
