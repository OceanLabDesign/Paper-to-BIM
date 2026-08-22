"""s03_lines —— 線段偵測

規格：v0.4 §8、參數見 core/config.py（§10）
輸入：{case}/01_tiles_upright/*.png ＋ {case}/01_offsets.csv
      （**必須吃轉正後的片**：offsets 的 x/y 已由 s01b 依 rotation 重算過，
        配未轉正的片會整片偏掉 —— 裁決 §1）
輸出：{case}/03_lines.csv

要點：**自適應二值化 (ADAPTIVE_BLOCK, ADAPTIVE_C) = (31, 12)，禁用 Otsu。**
      座標經 offsets 轉為**整頁座標系**後才寫檔（不要留片內座標）。
閘門：疊圖目視 —— 牆心線壓真牆（§11 第 3 步）。

禁：不要重新調參。那組數字是曬圖陰影下活下來的實測值。
"""

import csv
from pathlib import Path

from core import case, fields
from core.config import (ADAPTIVE_BLOCK, ADAPTIVE_C, HOUGH_THRESHOLD,
                         MIN_LINE_LENGTH, MAX_LINE_GAP)


def detect_lines(gray):
    """灰階 → 線段清單。參數一律取自 core.config（§10 實測值），不在這裡調。"""
    import cv2
    import numpy as np
    b = cv2.adaptiveThreshold(gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
                              cv2.THRESH_BINARY_INV, ADAPTIVE_BLOCK, ADAPTIVE_C)
    ls = cv2.HoughLinesP(b, 1, np.pi / 180, HOUGH_THRESHOLD,
                         minLineLength=MIN_LINE_LENGTH, maxLineGap=MAX_LINE_GAP)
    return [] if ls is None else [tuple(int(v) for v in l) for l in ls[:, 0]]


def run(case_dir: Path, tiles=None) -> int:
    """對每片跑線段偵測，寫 03_lines.csv。回傳線段數。

    ⚠ 座標是**片內座標**，不是整頁座標系。這批掃描沒有拼版、也不做像素對位
    （ADR 0009），所以整頁座標系並不存在 —— tile_id 就是座標系的識別。
    """
    import cv2
    import math
    case_dir = Path(case_dir)
    offsets = list(csv.DictReader(case.path(case_dir, "offsets").open(encoding="utf-8")))
    if tiles:
        offsets = [o for o in offsets if o["tile_id"] in tiles]
    rows, n = [], 0
    for o in offsets:
        tid = o["tile_id"]
        gray = cv2.imread(str(case_dir / o["upright_file"]), 0)
        for x1, y1, x2, y2 in detect_lines(gray):
            n += 1
            rows.append({"line_id": f"{tid}_l{n:05d}", "sheet_id": "", "tile_id": tid,
                         "wkt": f"LINESTRING({x1} {y1}, {x2} {y2})",
                         "length_px": round(math.hypot(x2 - x1, y2 - y1), 1),
                         "angle_deg": round(math.degrees(math.atan2(y2 - y1, x2 - x1)) % 180, 1),
                         "thickness_px": "", "quality_zone": ""})
    with case.path(case_dir, "lines").open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fields.LINES); w.writeheader(); w.writerows(rows)
    return n
