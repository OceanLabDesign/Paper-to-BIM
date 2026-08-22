"""s01c_register —— 片間對位：從散亂掃描片求出整頁座標系

規格：ADR 0008（散開的掃描影像如何進入座標系）
輸入：{case}/01_tiles_upright/*.png（已轉正）
輸出：{case}/01_registration.csv（**候選與證據，不是定案**）

## 這支只提候選，不做定案

規格 §8 的原路是「偏移量從 PDF 的放置矩陣讀」。輸入若是散開的掃描片，
那個矩陣不存在，就得自己算。但**算出來的東西不會直接寫進 01_offsets.csv** ——
它帶著證據進 01_registration.csv，由中樞裁定（ADR 0008 選項 D）。

理由是失敗模式：盲拼接失敗時**圖看起來是完整的，只是尺寸全錯，要量過才知道**。
放在中樞層之後，對不起來就變成一筆矛盾傳給人，跟其他矛盾一樣。

## 為什麼不用一般的影像拼接

實測過三種，用合成測資（真值已知）量誤差 —— 見 tests/test_register.py：

| 方法 | 結果 |
|---|---|
| 相位相關（phase correlation） | 7 對全錯，誤差 355–920 px。重疊只有 20%，相關峰被非重疊區蓋掉 |
| ORB 特徵點 ＋ RANSAC | 7 對全錯。**曬圖平面圖全是等距平行線，點特徵大量誤配** —— 而且會給出 41/107 內點這種看起來很有信心的錯答案 |
| 投影剖面 ＋ 墨水一致度（本模組） | 5/7 完全正確（誤差 0 px），其餘 2 對**證據不足、據實回報** |

## 做法

建築平面是**軸對齊**的 —— 牆、尺寸線、圖框幾乎都水平或垂直。所以：

1. 自適應二值化（core.config 的 31, 12），與 s03_lines 同一組參數
2. 墨水沿列／沿行加總得兩條 1D 剖面，各自互相關 → x 與 y 的候選**獨立**求解，
   搜尋空間從 O(W·H) 降到 O(W)+O(H)
3. 以剖面候選為錨，在重疊區算**墨水一致度**（不是相關係數 ——
   相關係數會被白紙騙，白紙對白紙 r=1.0）
4. 證據門檻：重疊面積與重疊區墨水量都要夠。不夠就回報 insufficient_evidence

## 已知限制（誠實的那種）

長平行線沿自己的方向滑動時重疊幾乎不變，所以：
**窄重疊帶裡若沒有垂直線，dx 就無法由像素決定**（反之亦然）。
這不是調參可以解決的，是那條帶子上沒有證據。
遇到時本模組回報低信心，交給全域求解繞路，繞不過就交給中樞。
"""

import csv
import math
from pathlib import Path

MIN_OVERLAP_PX = 20000      # 重疊面積下限
MIN_INK_PX = 3000           # 重疊區各自的墨水下限 —— 白紙對白紙沒有證據
MIN_AGREE = 0.55            # 墨水一致度下限
MIN_DISTINCT = 1.15         # 最佳／次佳，太接近代表被重複結構騙了
DILATE = 5                  # 線寬只有 2px，比對要給容差
COARSE_STEP = 3

REGISTRATION = ("tile_a", "tile_b", "dx", "dy", "agree", "overlap_px",
                "ink_px", "distinct", "status", "note")
STATUS = ("ok", "low_distinct", "insufficient_evidence", "no_overlap")


def run(case_dir: Path) -> None:
    raise NotImplementedError(
        "s01c_register 的 case 層封裝未實作；核心演算法見本模組的 register_pair 與 solve_global，"
        "已用 tests/fixtures/scattered 的真值測過（tests/test_register.py）。"
    )


# ─────────────────────────────────────────────────────────────
# 核心演算法（不碰檔案系統，方便測）
# ─────────────────────────────────────────────────────────────

def prepare(gray):
    """灰階 → 二值墨水圖 ＋ 膨脹版。參數與 s03_lines 同一組（§10）。"""
    import cv2
    import numpy as np
    from core.config import ADAPTIVE_BLOCK, ADAPTIVE_C
    b = cv2.adaptiveThreshold(gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
                              cv2.THRESH_BINARY_INV, ADAPTIVE_BLOCK, ADAPTIVE_C)
    ink = (b > 0).astype(np.uint8)
    return ink, cv2.dilate(ink, np.ones((DILATE, DILATE), np.uint8))


def _profile_candidates(pa, pb, min_overlap=80, separation=20, k=3):
    """兩條 1D 剖面的最佳位移候選（非極大值抑制過）。"""
    import numpy as np
    na, nb = len(pa), len(pb)
    found = []
    for s in range(-nb + min_overlap, na - min_overlap + 1):
        i0, i1 = max(0, s), min(na, s + nb)
        if i1 - i0 < min_overlap:
            continue
        a, b = pa[i0:i1], pb[i0 - s:i1 - s]
        if a.std() < 1e-6 or b.std() < 1e-6:
            continue
        found.append((float(np.corrcoef(a, b)[0, 1]), s))
    found.sort(reverse=True)
    out = []
    for r, s in found:
        if all(abs(s - s2) >= separation for _, s2 in out):
            out.append((r, s))
        if len(out) >= k:
            break
    return out


def _agreement(A, Ad, B, Bd, dx, dy):
    """位移 (dx,dy) 下重疊區的墨水一致度。回傳 (一致度, 重疊面積, 較少的一方墨水量)。"""
    ha, wa = A.shape
    hb, wb = B.shape
    x0, y0 = max(0, dx), max(0, dy)
    x1, y1 = min(wa, dx + wb), min(ha, dy + hb)
    area = max(0, x1 - x0) * max(0, y1 - y0)
    if area < MIN_OVERLAP_PX:
        return -1.0, area, 0
    a = A[y0:y1, x0:x1]
    b = B[y0 - dy:y1 - dy, x0 - dx:x1 - dx]
    ia, ib = int(a.sum()), int(b.sum())
    if min(ia, ib) < MIN_INK_PX:
        return -1.0, area, min(ia, ib)          # 重疊區沒有足夠證據
    ad = Ad[y0:y1, x0:x1]
    bd = Bd[y0 - dy:y1 - dy, x0 - dx:x1 - dx]
    agree = int((a & bd).sum()) + int((b & ad).sum())
    return agree / (ia + ib), area, min(ia, ib)


def register_pair(gray_a, gray_b):
    """求 b 相對於 a 的位移。回傳 dict，status 說明可不可信。"""
    import numpy as np
    A, Ad = prepare(gray_a)
    B, Bd = prepare(gray_b)
    Af, Bf = A.astype(np.float32), B.astype(np.float32)
    cand_y = _profile_candidates(Af.sum(1), Bf.sum(1))
    cand_x = _profile_candidates(Af.sum(0), Bf.sum(0))

    scored = {}
    def try_at(dx, dy):
        key = (dx, dy)
        if key not in scored:
            scored[key] = _agreement(A, Ad, B, Bd, dx, dy)
        return scored[key]

    for _, dy in cand_y:                                  # y 錨定，掃 x
        for dx in range(-B.shape[1] + 60, A.shape[1] - 60, COARSE_STEP):
            try_at(dx, dy)
    for _, dx in cand_x:                                  # x 錨定，掃 y
        for dy in range(-B.shape[0] + 60, A.shape[0] - 60, COARSE_STEP):
            try_at(dx, dy)

    ranked = sorted(((v[0], k, v) for k, v in scored.items()), reverse=True)
    if not ranked or ranked[0][0] < 0:
        return dict(dx=0, dy=0, agree=0.0, overlap_px=0, ink_px=0,
                    distinct=0.0, status="insufficient_evidence",
                    note="沒有任何位移的重疊區具備足夠墨水")

    top_s, (dx, dy), (a_s, area, ink) = ranked[0]
    for ddx in range(-COARSE_STEP, COARSE_STEP + 1):       # 全解析度細修
        for ddy in range(-COARSE_STEP, COARSE_STEP + 1):
            s, ar, ik = try_at(dx + ddx, dy + ddy)
            if s > top_s:
                top_s, dx, dy, area, ink = s, dx + ddx, dy + ddy, ar, ik
    second = next((s for s, k, _ in ranked
                   if math.hypot(k[0] - dx, k[1] - dy) > 30), 0.0)
    distinct = top_s / second if second > 0 else float("inf")

    status = "ok"
    if top_s < MIN_AGREE:
        status = "insufficient_evidence"
    elif distinct < MIN_DISTINCT:
        status = "low_distinct"
    return dict(dx=int(dx), dy=int(dy), agree=round(top_s, 4),
                overlap_px=int(area), ink_px=int(ink),
                distinct=round(min(distinct, 99.0), 3), status=status,
                note="" if status == "ok" else "證據不足或被重複結構干擾，交由中樞裁定")


def solve_global(edges, tiles):
    """把兩兩位移接成整頁座標。只用 status=='ok' 的邊，從最強的開始長生成樹。

    回傳 (placement, used_edges, unplaced)。**繞得到路的片才給座標** ——
    繞不到的回報在 unplaced，不要用猜的補。
    """
    strong = sorted((e for e in edges if e["status"] == "ok"),
                    key=lambda e: -e["agree"])
    if not strong:
        return {}, [], list(tiles)
    placement, used = {}, []
    root = strong[0]["tile_a"]
    placement[root] = (0, 0)
    changed = True
    while changed:
        changed = False
        for e in strong:
            a, b = e["tile_a"], e["tile_b"]
            if a in placement and b not in placement:
                x, y = placement[a]
                placement[b] = (x + e["dx"], y + e["dy"]); used.append(e); changed = True
            elif b in placement and a not in placement:
                x, y = placement[b]
                placement[a] = (x - e["dx"], y - e["dy"]); used.append(e); changed = True
    # 平移到左上角為原點
    if placement:
        mx = min(p[0] for p in placement.values())
        my = min(p[1] for p in placement.values())
        placement = {k: (v[0] - mx, v[1] - my) for k, v in placement.items()}
    return placement, used, [t for t in tiles if t not in placement]


def closure_errors(placement, edges):
    """回路閉合檢查 —— 與尺寸鏈閉合同一個道理：多餘的邊拿來驗證，不是拿來平均。

    回傳沒被生成樹用到、但兩端都已定位的邊的殘差（px）。
    """
    out = []
    for e in edges:
        a, b = e["tile_a"], e["tile_b"]
        if a in placement and b in placement and e["status"] == "ok":
            (ax, ay), (bx, by) = placement[a], placement[b]
            err = math.hypot((bx - ax) - e["dx"], (by - ay) - e["dy"])
            out.append((a, b, round(err, 1)))
    return out
