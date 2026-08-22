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

import math

from core.config import PX_PER_CM, WALL_GAP_PX

DETECTOR_ID = "rule_v1"  # 裁決 §2：寫進 03_detections 的 detector 欄

ANGLE_TOL_DEG = 3.0      # 兩條線要多平行才算一對
MIN_OVERLAP = 0.45       # 投影重疊比例下限 —— 只是角度像不夠，要真的並排
MIN_LEN_PX = 90          # 太短的線對雜訊太多


def _line_geom(x1, y1, x2, y2):
    dx, dy = x2 - x1, y2 - y1
    length = math.hypot(dx, dy)
    ang = math.degrees(math.atan2(dy, dx)) % 180.0
    return length, ang, (dx / length, dy / length) if length else (0.0, 0.0)


def _angle_diff(a, b):
    d = abs(a - b) % 180.0
    return min(d, 180.0 - d)


def _dedup(cands, tol=12.0):
    """同一道牆會被不同的線對組合重複偵測到 —— 去掉幾乎相同的那些。

    注意這是**去重**不是**合併**：兩個端點都幾乎重合才算同一筆。
    共線但不重疊的兩段是兩道牆（或同一道牆被開口切斷），
    那要中樞判斷，偵測器不准擅自接起來。
    """
    kept = []
    for c in sorted(cands, key=lambda x: -math.dist(*x["axis"])):
        (ax, ay), (bx, by) = c["axis"]
        dup = False
        for k in kept:
            (kx, ky), (lx, ly) = k["axis"]
            same = (math.dist((ax, ay), (kx, ky)) < tol and math.dist((bx, by), (lx, ly)) < tol)
            flip = (math.dist((ax, ay), (lx, ly)) < tol and math.dist((bx, by), (kx, ky)) < tol)
            if same or flip:
                dup = True
                break
        if not dup:
            kept.append(c)
    return kept


def detect(lines, exclude=()):
    """從線段找平行線對 → 牆候選。

    lines：[(x1, y1, x2, y2), ...]（整數像素）
    exclude：[(x0, y0, x1, y1), ...] 排除帶（圖框、標題欄、印章區）——
             §8「排除帶內的線先剔」。中心落在排除帶內的候選一律丟棄。
    回傳：[{axis: ((x1,y1),(x2,y2)), thickness_px, thickness_cm, gap_px,
            angle_deg, overlap, members: (i, j)}]

    做法：同角度、投影有重疊、法向間距落在 core.config.WALL_GAP_PX 之內。
    §8 的規則之一。**不做的事**：不推測牆的端點延伸、不合併共線的牆 ——
    那是中樞的判斷，不是偵測器的。
    """
    prepped = []
    for i, (x1, y1, x2, y2) in enumerate(lines):
        L, ang, u = _line_geom(x1, y1, x2, y2)
        if L >= MIN_LEN_PX:
            prepped.append((i, (x1, y1, x2, y2), L, ang, u))

    lo, hi = WALL_GAP_PX
    out = []
    for a in range(len(prepped)):
        ia, (ax1, ay1, ax2, ay2), La, anga, (ux, uy) = prepped[a]
        for b in range(a + 1, len(prepped)):
            ib, (bx1, by1, bx2, by2), Lb, angb, _ = prepped[b]
            if _angle_diff(anga, angb) > ANGLE_TOL_DEG:
                continue
            # b 的兩端到 a 所在直線的法向距離
            nx, ny = -uy, ux
            d1 = (bx1 - ax1) * nx + (by1 - ay1) * ny
            d2 = (bx2 - ax1) * nx + (by2 - ay1) * ny
            if abs(d1 - d2) > 6:                      # 不平行（法向距離差太多）
                continue
            gap = abs((d1 + d2) / 2)
            if not (lo <= gap <= hi):
                continue
            # 沿 a 方向的投影重疊
            pa = sorted([(ax1 - ax1) * ux + (ay1 - ay1) * uy,
                         (ax2 - ax1) * ux + (ay2 - ay1) * uy])
            pb = sorted([(bx1 - ax1) * ux + (by1 - ay1) * uy,
                         (bx2 - ax1) * ux + (by2 - ay1) * uy])
            ov = min(pa[1], pb[1]) - max(pa[0], pb[0])
            if ov <= 0 or ov / min(La, Lb) < MIN_OVERLAP:
                continue
            # 牆心線＝兩線中線，長度取重疊段
            s0, s1 = max(pa[0], pb[0]), min(pa[1], pb[1])
            mx, my = (nx * (d1 + d2) / 4, ny * (d1 + d2) / 4)
            out.append({
                "axis": ((ax1 + ux * s0 + mx, ay1 + uy * s0 + my),
                         (ax1 + ux * s1 + mx, ay1 + uy * s1 + my)),
                "thickness_px": round(gap, 1),
                "thickness_cm": round(gap / PX_PER_CM, 1),
                "gap_px": round(gap, 1), "angle_deg": round(anga, 1),
                "overlap": round(ov / min(La, Lb), 2), "members": (ia, ib),
            })

    if exclude:
        def outside(c):
            cx = (c["axis"][0][0] + c["axis"][1][0]) / 2
            cy = (c["axis"][0][1] + c["axis"][1][1]) / 2
            return not any(x0 <= cx <= x1 and y0 <= cy <= y1 for x0, y0, x1, y1 in exclude)
        out = [c for c in out if outside(c)]
    return _dedup(out)
