"""tests/test_seam.py —— L3 接縫對位的可行性驗證（需要真實案件資料）

`python3 tests/test_seam.py`

驗的不是「能不能算出一個答案」，是「答案可不可信」。
沒有真實案件資料時自動跳過 —— 案件資料不進版控（.gitignore 的 cases/**）。

## 這支測試的由來

2026-08-22 驗證 L3 是否可行時得到的結論，逐條記在下面，
因為它們每一條都是踩過的坑：

1. **單一配對的分數不可信。** S04 的局部分數說 TL=p14（0.189 vs 0.062，
   還落在「清楚」區），但目視確認 p15 才對 —— p15 下緣與 p16 上緣是同一片內容
   （同一個「逃生梯」手寫標註、同一組「火警受信總機」直書字、右端同樣的 36+PB）。
2. **跨組一致性抓得到那個錯。** 十一組裡有十組的 TL 都落在該組的第 3 頁，
   對應掃描順序「右下→右上→左上→左下」。S04 是唯一例外，因而被標記。
   這與尺寸鏈閉合是同一個道理：多餘的觀測拿來驗證，不是拿來平均。
3. **反例要設計對。** 第一版拿「BL 左緣 ↔ BR 右緣」當反例，但那是整張大圖的
   最外緣、都貼著圖框，本來就虛假相關 —— 導致誤判方法無效。
   正確的反例是「把下排的片放到下排上方」，那在物理上不可能，得分應為 0。
"""

import csv
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.dont_write_bytecode = True

CASE = ROOT / "cases" / "79-B37001_七賢二路"
BAND = 80
CLEAR_GAP = 0.10          # 勝出與次佳的差距門檻


def _need_numpy_cv():
    import numpy, cv2                                          # noqa: F401
    return numpy, cv2


def _edge(tid, side, cache={}):
    np, cv2 = _need_numpy_cv()
    if tid not in cache:
        im = cv2.imread(str(CASE / "01_tiles_upright" / f"{tid}.png"), 0)
        b = (cv2.adaptiveThreshold(im, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
                                   cv2.THRESH_BINARY_INV, 31, 12) > 0).astype("float32")
        r, c = b.sum(1), b.sum(0)
        ys = np.where(r > r.max() * 0.02)[0]
        xs = np.where(c > c.max() * 0.02)[0]
        cache[tid] = (b, (xs[0], ys[0], xs[-1], ys[-1]))        # 去掉影印機的白邊
    b, (x0, y0, x1, y1) = cache[tid]
    return (b[y0:y0 + BAND, x0:x1].sum(0) if side == "top"
            else b[y1 - BAND:y1, x0:x1].sum(0))


def _score(a, b, max_shift=250):
    np, _ = _need_numpy_cv()
    n = min(len(a), len(b)); a, b = a[:n], b[:n]
    best = 0.0
    for s in range(-max_shift, max_shift + 1, 2):
        i0, i1 = max(0, s), min(n, n + s)
        u, v = a[i0:i1], b[i0 - s:i1 - s]
        if len(u) < n * 0.6 or u.std() < 1e-6 or v.std() < 1e-6:
            continue
        best = max(best, float(np.corrcoef(u, v)[0, 1]))
    return best


def main() -> int:
    if not (CASE / "01_tiles_upright").exists():
        print("跳過：沒有真實案件資料（cases/** 不進版控）")
        return 0
    try:
        _need_numpy_cv()
    except ImportError:
        print("跳過：需要 numpy 與 opencv-python")
        return 0

    from core.case import path as cpath
    rows = list(csv.DictReader(cpath(CASE, "sheet_tiles").open(encoding="utf-8")))
    sheets = {}
    for r in rows:
        sheets.setdefault(r["sheet_id"], []).append(r)

    verdicts, bad = {}, []
    for sid, g in sorted(sheets.items()):
        bl = next((x["tile_id"] for x in g if x["col"] == "0" and x["status"] == "assigned"), None)
        br = next((x["tile_id"] for x in g if x["col"] == "1" and x["status"] == "assigned"), None)
        unk = [x["tile_id"] for x in g if x["status"] == "ambiguous"]
        if not (bl and br and len(unk) == 2):
            continue
        ranked = sorted(((_score(_edge(u, "bot"), _edge(bl, "top")), u) for u in unk), reverse=True)
        impossible = _score(_edge(br, "bot"), _edge(bl, "top"))
        gap = ranked[0][0] - ranked[1][0]
        clear = gap > CLEAR_GAP and ranked[0][0] - impossible > CLEAR_GAP
        verdicts[sid] = {"tl": ranked[0][1], "gap": round(gap, 3), "clear": clear,
                         "impossible": round(impossible, 3)}

    # 反例必須拿低分 —— 這是方法有沒有鑑別力的關鍵
    imps = [v["impossible"] for v in verdicts.values()]
    zeroish = sum(1 for x in imps if x < 0.10)
    print(f"[1] 反例（把下排的片放到下排上方）：{zeroish}/{len(imps)} 組低於 0.10")
    if zeroish < len(imps) * 0.7:
        bad.append(f"反例只有 {zeroish}/{len(imps)} 拿低分 —— 方法沒有鑑別力")

    # 跨組一致性：TL 應落在各組的同一個序位
    order = {}
    for sid, g in sheets.items():
        ids = sorted(x["tile_id"] for x in g)
        if sid in verdicts:
            order[sid] = ids.index(verdicts[sid]["tl"])
    from collections import Counter
    c = Counter(order.values())
    major, n_major = c.most_common(1)[0]
    outliers = [s for s, i in order.items() if i != major]
    print(f"[2] 跨組一致性：{n_major}/{len(order)} 組的 TL 落在第 {major+1} 序位"
          f"｜例外 {outliers or '無'}")
    if n_major < len(order) * 0.7:
        bad.append(f"跨組一致性不足（{n_major}/{len(order)}），掃描順序假設不成立")

    clear = [s for s, v in verdicts.items() if v["clear"]]
    print(f"[3] 局部判定清楚：{len(clear)}/{len(verdicts)} 組")

    # ★ 已知事實：S04 的局部分數是錯的（目視確認 p15 才對），要被一致性抓出來
    if "S04" in verdicts and verdicts["S04"]["tl"] == "p14" and "S04" not in outliers:
        bad.append("S04 的局部誤判沒有被跨組一致性抓到 —— 那道檢查失效了")
    print(f"[4] S04（已知局部誤判）：局部說 {verdicts.get('S04',{}).get('tl','?')}、"
          f"一致性{'有' if 'S04' in outliers else '沒有'}標記為例外")

    if bad:
        print("\n✗ " + "；".join(bad))
        return 1
    print("\n✓ L3 可行：局部分數不可單獨採信，配上跨組一致性才成立")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
