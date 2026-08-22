"""planning/fake_proposer.py —— 假中樞（回固定計畫）

規格：v0.4 §0.3、§11 第 5 步。

用途：**迴圈、驗收、執行、對照全部先用假中樞驗通**，真中樞接上時只剩一個變因。
簽章與 proposer.propose_plan() 完全一致，可直接替換。

假中樞回的是寫死的 plan：68 年案手寫計畫，結構照 §6.1（格式參考
examples/plan_vN.sample.yaml），但 **id 必須是真實 CSV 裡查得到的** ——
範例檔的 id 是假的，直接拿來用會被 validate 規則 2 退件。
它必須**通得過 validate 六條** —— 不然驗不到迴圈，只驗到退件。
"""

import csv
import re
from pathlib import Path

from core import case
from core.config import PX_PER_CM


def _endpoints(wkt):
    pts = re.findall(r"(-?\d+(?:\.\d+)?) (-?\d+(?:\.\d+)?)", wkt)
    return [(float(x), float(y)) for x, y in pts]


def propose_plan(case_dir, version: int = 1, residuals=None, rejected=None,
                 tile=None, min_conf=0.0) -> dict:
    """把 03_detections 的牆候選原樣搬成 plan 的 judgments。

    **這不是中樞。** 它不判斷、不推翻標籤、不寫 conflicts —— 只是把偵測結果
    包成合法的 plan，好讓迴圈的其餘部分（驗收 → 執行 → 對照）可以先被驗通。
    §11 第 5 步先於第 6 步是刻意的：真中樞接上時只剩一個變因。

    座標換算：像素 → 公分（÷ PX_PER_CM），Y 軸翻轉（影像 Y 向下、CAD Y 向上）。
    """
    case_dir = Path(case_dir)
    dets = [r for r in csv.DictReader(case.path(case_dir, "detections").open(encoding="utf-8"))
            if (tile is None or r["det_id"].startswith(tile))
            and float(r["conf"]) >= min_conf]
    sheets = list(csv.DictReader(case.path(case_dir, "sheets").open(encoding="utf-8")))
    ctx = sheets[0] if sheets else {}

    judgments = []
    for i, d in enumerate(dets, 1):
        (x1, y1), (x2, y2) = _endpoints(d["bbox_wkt"])
        ax1, ay1 = x1 / PX_PER_CM, -y1 / PX_PER_CM
        ax2, ay2 = x2 / PX_PER_CM, -y2 / PX_PER_CM
        judgments.append({
            "id": f"J{i:04d}", "type": "wall",
            "geometry": {"axis_wkt": f"LINESTRING({ax1:.1f} {ay1:.1f}, {ax2:.1f} {ay2:.1f})"},
            "evidence": [f"det#{d['det_id']}"],
            "confidence": float(d["conf"]),
            "note": "假中樞：偵測結果原樣搬運，未經判斷",
        })
    return {
        "meta": {"case": case_dir.name, "sheet": ctx.get("sheet_id", ""),
                 "version": version, "based_on": None},
        "context": {"kind": ctx.get("kind", ""), "floor": ctx.get("drawing_floor", ""),
                    "scale": ctx.get("scale", ""), "unit": "cm",
                    "orientation": ctx.get("orientation", "")},
        "judgments": judgments, "overrides": [], "conflicts": [],
        "uncertain": [], "residual_handling": [],
    }
