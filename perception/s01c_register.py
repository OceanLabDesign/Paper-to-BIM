"""s01c_register —— 把片放進圖座標系（**候選與證據，不是定案**）

規格：ADR 0011（補上度量層 —— 拼座標不拼像素）
輸入：{case}/01_tiles_upright/*.png（已轉正）
      {case}/02_sheet_tiles.csv（哪些片屬於同一張圖 —— **這支不負責分組**）
      {case}/02_understanding_*.json（有的話：尺寸鏈，用來校比例尺）
輸出：{case}/01_placement.csv（`core.fields.PLACEMENT`）

    python3 -m perception.s01c_register cases/<案號_地段>

## 這支只提候選，不做定案

沿用 ADR 0008 留下的契約（機制被 ADR 0011 換掉，檔名保留 —— 改名會動到 §8 模組表）。
`status` 一律 `candidate` / `conflict` / `unresolved`，**沒有 `assigned`**。
定案是中樞的事。

## 不做像素配準

ADR 0009 量過五種像素配準（registration）在曬圖平面圖上全數失敗，
共同失敗模式是**理直氣壯地錯**（`findTransformECC` 在錯答案上給 cc=1.0000）。
這支一條像素配準都不用，錨點全部來自圖上明寫的東西。

## 證據四階

| tier | 錨點 | 給出 | 本檔狀態 |
|---|---|---|---|
| 1 | 尺寸鏈跨縫閉合 | 偏移量＋比例尺 | **比例尺已實作**；跨縫偏移待判讀涵蓋相鄰片 |
| 2 | 圖框（drawing frame） | 該軸偏移量＋哪幾側是外緣 | **已實作** |
| 3 | 基準線延續 | 該軸偏移量 | 未實作（等判讀輸出軸線） |
| 4 | 接縫重疊帶對齊 | x 軸偏移量 | **已實作，但只在標題欄那列**（見下） |
| 9 | 網格標稱值 | 兩軸偏移量 | 後備，低信心 |

**未實作的階不是佔位**：沒有輸入資料就算不出來，硬做出來的數字比沒有更危險。

## tier 4 只在標題欄那一列量得準

2026-08-23 在 25 張圖上量了兩列各自的水平接縫偏移（獨立的冗餘量測，兩列理應相同）：

| 量在哪 | 結果 | IoU |
|---|---|---|
| **下列（有標題欄）** | 19/25 落在 3344–3864 的窄帶 | 0.13–0.31 |
| 上列（純平面圖） | 1336–4632，完全散開 | 0.02–0.27 |

兩列一致（±40px）只有 **2/25**。原因不是演算法：平面圖上滿是等距平行線，
正是 ADR 0009 記的那個失敗模式；標題欄是不重複的文字，才對得起來。

**所以不要在平面圖內容上找接縫。** 而且不必找 —— 影印機是沿一條垂直線一刀切，
整張圖只有一個水平偏移，在標題欄那列量準了套用到所有列即可。

⚠ **峰值比（peak/median）不是信心。** 實測 p06→p03 的峰值比只有 2.68×（四組最低）
卻是對的（目視確認被切斷的「梁慶」正好疊上「梁慶源」）。
可信的檢查是**冗餘**：全案的偏移量應該相近（同一台影印機、同一個操作者），
離群的那幾張要當矛盾回報，不要當成量出來的值。

## 圖框偵測要掃歪斜

曬圖掃描每張的歪斜不同，而且**同一張的四個邊最佳角度還不一樣**
（p07 實測：底邊 +1.20°、右邊 +0.45° —— 紙本身有變形）。
不掃角度的話一條斜 1° 的框線會攤平在 26 個像素列上，每列都達不到門檻。
實測：不掃角度時 12 片只有 3 片點火；掃 ±1.5° 之後 p03 底邊從 0.46 升到 0.90。
"""

import csv
import json
import math
import sys
from pathlib import Path

import cv2
import numpy as np

from core import case as C
from core import fields as F

MODULE_ID = "s01c_v2"          # v1 是 ADR 0008 的像素配準，已廢

# 圖框偵測
BAND = 500                     # 從邊往內看多深（px）
LINE_MIN = 0.55                # 線上墨水佔該邊長度的比例，達標才算框線
OUTSIDE_MAX = 0.025            # 線外側平均墨水，超過就不是紙的留白
SKEW_RANGE, SKEW_STEP = 1.5, 0.15   # 掃歪斜的範圍與步長（度）
SIDES = ("top", "right", "bottom", "left")


# ── tier 2：圖框 ──────────────────────────────────────────────────────────
def _profile(binary, side, angle):
    """把二值圖轉 angle 度之後，取該邊往內 BAND 深的墨水剖面。

    剖面的 index 0 一律是**最靠外**那一列 —— 四個邊統一方向，下游才不必分邊處理。
    """
    h, w = binary.shape
    if angle:
        m = cv2.getRotationMatrix2D((w / 2, h / 2), angle, 1.0)
        binary = cv2.warpAffine(binary, m, (w, h),
                                flags=cv2.INTER_NEAREST, borderValue=0)
    if side == "top":
        return binary[:BAND].sum(axis=1) / 255.0 / w
    if side == "bottom":
        return binary[h - BAND:][::-1].sum(axis=1) / 255.0 / w
    if side == "left":
        return binary[:, :BAND].sum(axis=0) / 255.0 / h
    return binary[:, w - BAND:][:, ::-1].sum(axis=0) / 255.0 / h


def frame_edges(gray) -> dict:
    """每一側找「外側乾淨、線上濃」的最外一條長直線。

    **外側乾淨才是判準的重點** —— 那代表紙的留白，也就是整張大圖的外緣。
    線很濃但外側還有內容，那是圖裡的線（表格邊、牆），不是圖框。

    回傳 {side: {"dist","strength","angle"} 或 None}。
    dist 是框線離該邊幾 px（已計入歪斜校正）。
    """
    b = cv2.adaptiveThreshold(gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
                              cv2.THRESH_BINARY_INV, 31, 12)
    out = {}
    for side in SIDES:
        best = None
        for a in np.arange(-SKEW_RANGE, SKEW_RANGE + 1e-9, SKEW_STEP):
            prof = _profile(b, side, float(a))
            for d in np.where(prof >= LINE_MIN)[0]:
                if d < 8:                                   # 太靠邊的是掃描雜訊
                    continue
                if float(prof[:d].mean()) >= OUTSIDE_MAX:   # 外側還有內容 → 不是圖框
                    continue
                cand = {"dist": int(d), "strength": round(float(prof[d]), 3),
                        "angle": round(float(a), 2)}
                if best is None or cand["strength"] > best["strength"]:
                    best = cand
                break
        out[side] = best
    return out


# ── tier 1：尺寸鏈校比例尺 ────────────────────────────────────────────────
def scale_from_chains(dims: dict, regions: dict):
    """從**閉合的**尺寸鏈反推 px_per_cm（整片像素）。

    只用有兩段以上的鏈 —— 鏈能交叉驗證本身就是驗算，這正是像素配準沒有的東西。
    對不上的鏈不參與，也不去調它的數字（§1「矛盾是產出，不是障礙」）。

    ⚠ **座標空間要換算對。** 判讀是分區塊做的，`from`/`to` 是**該區塊內的比例座標**；
    區塊 meta 的 `w`/`h` 是裁切在整片裡的像素大小，`scale` 是存 PNG 時的縮小率。
    所以整片像素 = 比例 × w（**不乘 scale**）。
    踩過一次：拿判讀者在縮圖上量的 px/cm 直接跟 config.PX_PER_CM 比，
    得出「差 13%」的錯誤結論，實際只差 3.7%。

    回傳 (px_per_cm, evidence) 或 (None, 理由)。
    """
    got = []
    for r in dims.get("regions", []):
        m = regions.get(r.get("region"))
        if not m:
            continue
        for d in r.get("dims", []):
            if d.get("kind") != "dim" or not d.get("chain"):
                continue
            f, t = d.get("from") or [], d.get("to") or []
            try:
                cm = float(str(d.get("value", "")).strip())
            except ValueError:
                continue
            if len(f) != 2 or len(t) != 2 or cm <= 0:
                continue
            px = math.hypot((t[0] - f[0]) * m["w"], (t[1] - f[1]) * m["h"])
            if px > 0:
                got.append((d["chain"], px / cm))
    if not got:
        return None, "沒有帶端點的尺寸標註"
    per_chain = {}
    for chain, ratio in got:
        per_chain.setdefault(chain, []).append(ratio)
    ratios = [x for v in per_chain.values() if len(v) >= 2 for x in v]
    if not ratios:
        return None, f"有 {len(got)} 筆尺寸但沒有兩段以上的鏈可交叉驗證"
    med = float(np.median(ratios))
    spread = float(np.std(ratios) / med) if med else 1.0
    ev = (f"{len(ratios)} 段／{len(per_chain)} 條鏈，中位數 {med:.3f} px/cm，"
          f"離散度 {spread:.1%}")
    return (med, ev) if spread < 0.25 else (None, "各段比例尺不一致：" + ev)


# ── tier 4：沿已知接縫找偏移 ──────────────────────────────────────────────
SEAM_BAND_H = (0.86, 1.00)     # 左右相鄰：用底緣的標題欄帶。文字不重複，比平面圖好對
SEAM_BAND_V = (0.00, 1.00)     # 上下相鄰：沒有等價的帶子，只能用整片
SEAM_MIN_OVERLAP = 300         # 重疊少於這個就別談了
SEAM_COARSE, SEAM_FINE = 0.25, 4    # 粗掃的縮小率、細掃的步長（原尺度 px）


def _ink(gray, lo, hi, axis_h=True):
    h, w = gray.shape
    sub = gray[int(h * lo):int(h * hi)] if axis_h else gray[:, int(w * lo):int(w * hi)]
    b = cv2.adaptiveThreshold(sub, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
                              cv2.THRESH_BINARY_INV, 31, 12)
    return (b > 0).astype(np.float32)


def _iou(a, b):
    inter = float((a * b).sum())
    union = float(((a + b) > 0).sum())
    return inter / union if union > 500 else 0.0


def seam_offset(left, right, horizontal=True):
    """左右（或上下）相鄰兩片，沿已知接縫找偏移。

    **拓樸必須先確定。** 這支不判斷「這兩片相不相鄰」—— 那是排圖那一步用
    標題欄定的。這裡只在已知相鄰的前提下找一維偏移，搜尋空間小得多。
    ADR 0009 的五次失敗是在「不知道誰跟誰相鄰」的前提下做的，不是同一個問題。

    ⚠ **峰值比不是信心。** 實測 p06→p03 的峰值/中位數只有 2.68×（四組最低），
    但目視確認它是對的 —— 被切斷的「梁慶」正好疊上「梁慶源」。
    所以回傳的 ratio 只當**證據**寫進 CSV，不要拿它當自動採信的門檻。
    真正的驗證是語意的：對齊之後接縫兩側的字接不接得起來（見 verify_seam）。

    回傳 (offset, cross, iou, ratio) —— cross 是垂直於接縫的那一軸的偏移。
    """
    lo, hi = SEAM_BAND_H if horizontal else SEAM_BAND_V
    A = _ink(left, lo, hi, axis_h=horizontal)
    B = _ink(right, lo, hi, axis_h=horizontal)
    if not horizontal:                       # 上下相鄰：轉置成左右問題，共用同一段程式
        A, B = A.T, B.T
    n = A.shape[1]

    def scan(step, lohi, cross_range, scale):
        a = cv2.resize(A, (0, 0), fx=scale, fy=scale, interpolation=cv2.INTER_AREA)
        b = cv2.resize(B, (0, 0), fx=scale, fy=scale, interpolation=cv2.INTER_AREA)
        h2, w2 = a.shape
        out = []
        for d in range(lohi[0], lohi[1], max(1, int(step * scale))):
            ov = w2 - d
            if ov < SEAM_MIN_OVERLAP * scale:
                continue
            aa0 = a[:, d:]
            for c in cross_range:
                cc = int(c * scale)
                bb = b[:, :ov]
                if cc > 0:
                    x, y = aa0[cc:], bb[:h2 - cc]
                elif cc < 0:
                    x, y = aa0[:h2 + cc], bb[-cc:]
                else:
                    x, y = aa0, bb
                out.append((_iou(x, y), int(d / scale), c))
        out.sort(reverse=True)
        return out

    coarse = scan(40, (int(n * 0.25 * SEAM_COARSE), int(n * SEAM_COARSE)),
                  range(-160, 161, 20), SEAM_COARSE)
    if not coarse:
        return None
    _s, d0, c0 = coarse[0]
    fine = scan(SEAM_FINE, (max(0, d0 - 60), d0 + 60),
                range(c0 - 24, c0 + 25, 4), 1.0)
    best = fine[0] if fine else coarse[0]
    med = float(np.median([x[0] for x in coarse])) or 1e-6
    return {"offset": best[1], "cross": best[2], "iou": round(best[0], 3),
            "ratio": round(best[0] / med, 2)}


# ── 排列與擺放 ──────────────────────────────────────────────────────────
def outer_sides(frames: dict) -> tuple:
    """有圖框的那幾側，就是這片在整張大圖上的**外緣**。"""
    return tuple(s for s in SIDES if frames.get(s))


def sheet_dx(group: dict, tiles: dict) -> dict:
    """整張圖的水平接縫偏移。**只在標題欄那一列量**（見檔頭）。

    影印機沿一條垂直線一刀切，所以一個 col 邊界只有一個 dx，套用到所有列。
    回傳 {col_boundary: {offset, cross, iou, ratio, measured_row}}。
    """
    cells = group["cells"]
    rows = sorted({r for r, _ in cells})
    cols = sorted({c for _, c in cells})
    tb_rows = [r for r in rows
               if any(tiles.get(cells.get((r, c)), {}).get("has_tb") for c in cols)]
    row = tb_rows[-1] if tb_rows else (rows[-1] if rows else None)
    out = {}
    if row is None:
        return out
    for i in range(len(cols) - 1):
        a, b = cells.get((row, cols[i])), cells.get((row, cols[i + 1]))
        if not (a and b):
            continue
        r = seam_offset(tiles[a]["gray"], tiles[b]["gray"], horizontal=True)
        if r:
            out[cols[i]] = {**r, "measured_row": row,
                            "pair": f"{a}→{b}", "from_tb": row in tb_rows}
    return out


def place(group: dict, tiles: dict, dxs: dict, px_per_cm, med_dx=None) -> list:
    """算每片左上角在圖座標系的 (dx, dy)。原點是整張圖的**左上**框角。

    x：接縫量測（tier 4）→ 圖框左緣（tier 2）→ 網格標稱（tier 9）
    y：圖框上緣（tier 2）→ 網格標稱（tier 9）。**沒有可靠的水平接縫量測** ——
       上下相鄰處沒有標題欄那種不重複的內容可對。

    ⚠ 右緣／下緣的圖框量測只進 evidence 不進 dx/dy：它量的是「離整張圖右緣多遠」，
    要換算成絕對座標得先知道整張圖多寬，而寬度要等接縫全定了才知道。
    """
    cells = group["cells"]
    rows = sorted({r for r, _ in cells})
    cols = sorted({c for _, c in cells})
    out = []
    for (r, c), tid in sorted(cells.items()):
        t = tiles[tid]
        fr, tw, th = t["frames"], t["w"], t["h"]
        method, ev, note = [], [], []
        tier_x = tier_y = 9

        x = 0                                      # 由最左行往右累加接縫偏移
        ok = True
        for i in range(cols.index(c)):
            d = dxs.get(cols[i])
            if not d:
                ok = False
                break
            x += d["offset"]
        if ok and cols.index(c) > 0:
            tier_x = 4
            d = dxs[cols[cols.index(c) - 1]]
            method.append("seam")
            ev.append(f"接縫 {d['pair']} offset={d['offset']} iou={d['iou']}")
            if med_dx and abs(d["offset"] - med_dx) > 0.15 * med_dx:
                note.append(f"接縫偏移 {d['offset']} 偏離全案中位數 {med_dx}，可疑")
                tier_x = 9
        elif cols.index(c) == 0:
            if fr.get("left"):
                x, tier_x = -fr["left"]["dist"], 2
                method.append("left_frame"); ev.append(f"left@{fr['left']['dist']}px")
            else:
                x = 0
                method.append("origin_col0")
                tier_x = 2 if any(dxs.values()) else 9
        if tier_x == 9 and cols.index(c) > 0:
            x = cols.index(c) * tw
            method.append("grid_nominal_x"); note.append("x 無可用接縫")

        y = None                                   # y 只有圖框上緣給得出絕對值
        if fr.get("top"):
            y, tier_y = -fr["top"]["dist"], 2
            method.append("top_frame"); ev.append(f"top@{fr['top']['dist']}px")
        if fr.get("right"):
            ev.append(f"right@{fr['right']['dist']}px（需整張圖寬度才能換算）")
        if fr.get("bottom"):
            ev.append(f"bottom@{fr['bottom']['dist']}px（需整張圖高度才能換算）")
        if y is None:
            y = rows.index(r) * th
            method.append("grid_nominal_y"); note.append("y 無錨點")

        tier = min(tier_x, tier_y)
        conf = {2: 0.75, 4: 0.7, 9: 0.25}[tier]
        if tier_x <= 4 and tier_y == 2:
            conf = 0.85
        out.append({
            "tile_id": tid, "sheet_id": group["sheet_id"], "row": r, "col": c,
            "dx": round(x, 1), "dy": round(y, 1),
            "px_per_cm": "" if px_per_cm is None else round(px_per_cm, 4),
            "tier": tier, "method": "+".join(method) or "none",
            "evidence": "；".join(ev) or f"外緣 {outer_sides(fr) or '無'}",
            "conf": conf, "status": "candidate", "note": "；".join(note),
        })
    return out


# ── 入口 ──────────────────────────────────────────────────────────────────
def register(case_dir: Path) -> list:
    """**拓樸來自 02_sheet_tiles.csv，這支不重算。**

    那份是排圖那一步產出、而且人已經在介面上確認過的。程式重推一次會蓋掉人的判斷 ——
    人確認過的排列必須贏。缺 row/col 的片直接跳過並回報，不要猜。
    """
    case_dir = Path(case_dir)
    up = case_dir / "01_tiles_upright"
    st = case_dir / "02_sheet_tiles.csv"
    if not st.exists():
        raise FileNotFoundError(f"{st} 不存在 —— 先跑排圖（tools/arrange_ui.py）")

    frames = {}
    fp = case_dir / "01_frames.json"
    if fp.exists():
        frames = json.loads(fp.read_text(encoding="utf-8"))

    groups, skipped = {}, []
    for r in csv.DictReader(st.open(encoding="utf-8")):
        if r["row"] == "" or r["col"] == "":
            skipped.append(r["tile_id"]); continue
        g = groups.setdefault(r["sheet_id"],
                              {"sheet_id": r["sheet_id"], "cells": {}})
        g["cells"][(int(r["row"]), int(r["col"]))] = r["tile_id"]
    if skipped:
        print(f"  ⚠ {len(skipped)} 片沒有 row/col，跳過：{skipped[:6]}")

    regions = {}
    rm = case_dir / "02_regions" / "_meta.json"
    if rm.exists():
        regions = {m["key"]: m for m in json.loads(rm.read_text(encoding="utf-8"))}

    tb = {}
    tbf = case_dir / "02_titleblock_readings.json"
    if tbf.exists():
        tb = {r["tile_id"]: r for r in json.loads(tbf.read_text(encoding="utf-8"))}

    tiles = {}
    for g in groups.values():
        for tid in g["cells"].values():
            f = up / f"{tid}.png"
            if f.exists():
                gray = cv2.imread(str(f), 0)
                tiles[tid] = {"gray": gray, "w": gray.shape[1], "h": gray.shape[0],
                              "frames": frames.get(tid) or frame_edges(gray),
                              "has_tb": bool(tb.get(tid, {}).get("has_title_block"))}

    all_dx = {}
    for sid, g in sorted(groups.items()):
        all_dx[sid] = sheet_dx(g, tiles)
    vals = [d["offset"] for m in all_dx.values() for d in m.values()]
    med = int(np.median(vals)) if vals else None
    if med:
        print(f"  全案水平接縫偏移中位數 {med}px（重疊約 "
              f"{next(iter(tiles.values()))['w'] - med}px）")

    out = []
    for sid, g in sorted(groups.items()):
        ppc, ev = None, "未判讀"
        for tid in g["cells"].values():
            f = case_dir / f"02_dims_{tid}.json"
            if f.exists():
                ppc, ev = scale_from_chains(
                    json.loads(f.read_text(encoding="utf-8")), regions)
                ev = f"{tid}：{ev}"
                if ppc:
                    break
        rows = place(g, tiles, all_dx[sid], ppc, med)
        for r in rows:
            r["note"] = "；".join(x for x in (r["note"], f"比例尺：{ev}") if x)
        out += rows

    dst = case_dir / "01_placement.csv"
    with dst.open("w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=F.PLACEMENT)
        w.writeheader()
        w.writerows(out)
    return out


if __name__ == "__main__":
    if len(sys.argv) != 2:
        sys.exit(f"用法：python3 -m {__name__} cases/<案號_地段>")
    d = Path(sys.argv[1])
    rows = register(d)
    c = {}
    for r in rows:
        c[r["tier"]] = c.get(r["tier"], 0) + 1
    print(f"\n{len(rows)} 片 → {d / '01_placement.csv'}")
    print("  " + "　".join(f"tier {k}：{v} 片" for k, v in sorted(c.items())))
    sus = [r["tile_id"] for r in rows if "可疑" in r["note"]]
    if sus:
        print(f"  ⚠ 接縫偏移離群：{sus}")
    print("  ⚠ 全部是 candidate —— 定案是中樞的事（ADR 0011）")
