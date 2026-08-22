"""tests/fixtures/make_scattered.py —— 造「散亂掃描片」測資（含已知真值）

`python3 tests/fixtures/make_scattered.py` → tests/fixtures/scattered/

為什麼要這個：對位演算法不能靠「看起來對」驗收。這支畫一張像 1979 年建築平面的
合成圖，切成有重疊、**位移已知**的碎片，再加上曬圖劣化（底色不均、雜訊、模糊、
摺痕白帶）。演算法算出來的位移與 ground_truth.csv 差幾個 px，是可以量的。

刻意做得難：
  - 線畫稀疏且高度重複（平行牆線），這正是特徵點匹配最容易誤配的材料
  - 重疊區只有 15–25%，不是慷慨的 50%
  - 每片各自有不同的底色漸層與雜訊強度，模擬分次掃描
"""

import csv
import sys
from pathlib import Path

import numpy as np
import cv2

ROOT = Path(__file__).resolve().parents[2]
OUT = Path(__file__).resolve().parent / "scattered"

PX_PER_CM = 300 / 2.54 / 100          # 與 core.config 同一組換算：1:100、300dpi
W_CM, H_CM = 1200, 900                 # 建物 12m × 9m
MARGIN_CM = 150                        # 圖框留白 —— 尺寸鏈畫在這裡，真實圖面就是這樣


def cm(v):
    return int(round(v * PX_PER_CM))


def draw_plan(rng) -> np.ndarray:
    """畫一張平面圖：外牆線對、內牆、開口缺口、尺寸鏈、房間標記。

    建物四周留 MARGIN_CM 的白邊，尺寸鏈畫在那裡 —— 真實圖面就是這個構圖，
    而且那些標註是對位時最有辨識度的特徵（線畫本身太重複）。
    """
    M = cm(MARGIN_CM)
    W, H = cm(W_CM) + 2 * M, cm(H_CM) + 2 * M
    img = np.full((H, W), 255, np.uint8)
    ink = 40

    def P(x, y):
        """建物座標 → 畫布座標（含留白位移）。"""
        return cm(x) + M, cm(y) + M

    def wall(x1, y1, x2, y2, t_cm):
        """畫一道牆＝一對平行線（間距＝牆厚）。這是 §8 規則式偵測器要認的東西。"""
        t = cm(t_cm)
        (ax, ay), (bx, by) = P(x1, y1), P(x2, y2)
        if y1 == y2:
            for dy in (-t // 2, t // 2):
                cv2.line(img, (ax, ay + dy), (bx, by + dy), ink, 2)
        else:
            for dx in (-t // 2, t // 2):
                cv2.line(img, (ax + dx, ay), (bx + dx, by), ink, 2)

    # 外牆 24cm（1B 磚）
    for a, b, c, d in ((0, 0, W_CM, 0), (0, H_CM, W_CM, H_CM),
                       (0, 0, 0, H_CM), (W_CM, 0, W_CM, H_CM)):
        wall(a, b, c, d, 24)
    # 內牆 12cm（1/2B）—— 只隔 14px，是最容易糊掉的那種
    for a, b, c, d in ((0, 300, 500, 300), (500, 0, 500, 620),
                       (500, 620, W_CM, 620), (800, 300, 800, H_CM)):
        wall(a, b, c, d, 12)

    # 開口：把牆挖掉一段（門 90cm、窗 150cm）
    for x, y, w in ((120, 300, 90), (620, 620, 150), (500, 180, 90), (800, 750, 90)):
        (ax, ay) = P(x, y)
        cv2.rectangle(img, (ax, ay - cm(9)), (ax + cm(w), ay + cm(9)), 255, -1)

    # 尺寸鏈：長線 ＋ 兩端斜線 ＋ 數字方塊。橫向兩道（總尺寸與分段）、直向一道。
    def dim_run(x0, y0, parts, horizontal=True):
        pos = 0
        (sx, sy) = P(x0, y0)
        total = sum(parts)
        (ex, ey) = P(x0 + total, y0) if horizontal else P(x0, y0 + total)
        cv2.line(img, (sx, sy), (ex, ey), ink, 1)
        for i, seg in enumerate(parts + [0]):
            (tx, ty) = P(x0 + pos, y0) if horizontal else P(x0, y0 + pos)
            cv2.line(img, (tx - 7, ty + 7), (tx + 7, ty - 7), ink, 1)   # 兩端斜線
            if seg:
                (mx, my) = (P(x0 + pos + seg / 2, y0) if horizontal
                            else P(x0, y0 + pos + seg / 2))
                cv2.rectangle(img, (mx - 16, my - 30), (mx + 16, my - 14), ink, -1)
                pos += seg
    dim_run(0, -70, [500, 300, 400])                 # 上方分段鏈
    dim_run(0, -120, [1200])                          # 上方總尺寸
    dim_run(-70, 0, [300, 320, 280], horizontal=False)  # 左側直向鏈

    # 室名：小色塊，模擬中文字群（對位時最有辨識度的特徵）
    for x, y in ((200, 150), (700, 150), (200, 600), (900, 450), (350, 780), (1000, 120)):
        (ax, ay) = P(x, y)
        cv2.rectangle(img, (ax, ay), (ax + 70, ay + 24), ink, -1)

    # 圖框
    cv2.rectangle(img, (M // 3, M // 3), (W - M // 3, H - M // 3), ink, 2)
    return img


def degrade(tile, rng) -> np.ndarray:
    """曬圖劣化：底色漸層、雜訊、輕微模糊、一條摺痕白帶。"""
    h, w = tile.shape
    yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
    grad = (yy / h * rng.uniform(10, 35) + xx / w * rng.uniform(5, 25))
    out = tile.astype(np.float32) - grad + rng.uniform(-8, 8)
    out += rng.normal(0, rng.uniform(3, 9), out.shape)          # 掃描雜訊
    out = cv2.GaussianBlur(out, (0, 0), rng.uniform(0.6, 1.4))  # 針筆線擴散
    if rng.random() < 0.6:                                       # 摺痕白帶
        cx = rng.integers(w // 5, w * 4 // 5)
        band = np.clip(1.0 - np.abs(np.arange(w) - cx) / rng.uniform(8, 20), 0, 1)
        out += band[None, :] * rng.uniform(40, 90)
    return np.clip(out, 0, 255).astype(np.uint8)


def build(n_cols=3, n_rows=2, overlap=0.20, seed=68) -> Path:
    rng = np.random.default_rng(seed)
    page = draw_plan(rng)
    H, W = page.shape
    # 每片的名目大小（含重疊）
    tw = int(W / (n_cols - (n_cols - 1) * overlap))
    th = int(H / (n_rows - (n_rows - 1) * overlap))
    step_x, step_y = int(tw * (1 - overlap)), int(th * (1 - overlap))

    OUT.mkdir(parents=True, exist_ok=True)
    for f in OUT.glob("*"):
        f.unlink()
    truth = []
    for r in range(n_rows):
        for c in range(n_cols):
            x, y = c * step_x, r * step_y
            x, y = min(x, W - tw), min(y, H - th)
            # 掃描不會切得剛剛好：加一點隨機抖動
            jx, jy = int(rng.integers(-12, 13)), int(rng.integers(-12, 13))
            x, y = int(np.clip(x + jx, 0, W - tw)), int(np.clip(y + jy, 0, H - th))
            tile = degrade(page[y:y + th, x:x + tw], rng)
            tid = f"t{r}{c}"
            cv2.imwrite(str(OUT / f"{tid}.png"), tile)
            truth.append({"tile_id": tid, "x": x, "y": y, "w": tw, "h": th})

    with (OUT / "ground_truth.csv").open("w", newline="", encoding="utf-8") as f:
        wri = csv.DictWriter(f, fieldnames=["tile_id", "x", "y", "w", "h"])
        wri.writeheader()
        wri.writerows(truth)
    cv2.imwrite(str(OUT / "_page_reference.png"), page)      # 只給人看，程式不准讀
    return OUT


if __name__ == "__main__":
    p = build()
    print(f"✓ {p.relative_to(ROOT)}：{len(list(p.glob('t*.png')))} 片")
    import csv as _c
    rows = list(_c.DictReader((p / "ground_truth.csv").open(encoding="utf-8")))
    print(f"  片大小 {rows[0]['w']}×{rows[0]['h']} px，真值位移：")
    for r in rows:
        print(f"    {r['tile_id']}  x={r['x']:>5}  y={r['y']:>5}")
