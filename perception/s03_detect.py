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

import csv
import re
from pathlib import Path

from core import case, fields
from perception.detectors import rule


def _parse(wkt):
    a, b = re.findall(r"(-?\d+(?:\.\d+)?) (-?\d+(?:\.\d+)?)", wkt)
    return (float(a[0]), float(a[1]), float(b[0]), float(b[1]))


def run(case_dir: Path, exclude_by_tile=None) -> int:
    """讀 03_lines.csv，用 detectors/rule.py 找牆候選，寫 03_detections.csv。

    status 一律 `proposed` —— **標籤是主張不是事實**（§9）。
    改成 adopted/rejected 是中樞在 plan 裡裁定、由 orchestrator 回寫的事。
    """
    case_dir = Path(case_dir)
    by_tile = {}
    for r in csv.DictReader(case.path(case_dir, "lines").open(encoding="utf-8")):
        by_tile.setdefault(r["tile_id"], []).append((r["line_id"], _parse(r["wkt"])))
    rows, n = [], 0
    for tid, items in sorted(by_tile.items()):
        ids = [i for i, _ in items]
        cands = rule.detect([g for _, g in items],
                            exclude=(exclude_by_tile or {}).get(tid, ()))
        for c in cands:
            n += 1
            (x1, y1), (x2, y2) = c["axis"]
            ev = "|".join(f"line#{ids[i]}" for i in c["members"])
            rows.append({
                "det_id": f"{tid}_d{n:05d}", "sheet_id": "", "class_name": "wall",
                "bbox_wkt": f"LINESTRING({x1:.1f} {y1:.1f}, {x2:.1f} {y2:.1f})",
                "detector": rule.DETECTOR_ID,
                "conf": round(min(0.95, 0.4 + c["overlap"] * 0.5), 2),
                "evidence": ev, "provenance": rule.DETECTOR_ID,
                "quality_zone": "", "status": "proposed",
            })
    with case.path(case_dir, "detections").open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fields.DETECTIONS); w.writeheader(); w.writerows(rows)
    return n
