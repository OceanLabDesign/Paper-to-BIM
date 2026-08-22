"""s02_layout —— 版面判讀（VLM 一次呼叫）

規格：v0.4 §8、裁決 §1
輸入：{case}/01_tiles_upright/（**已轉正**）的整頁縮圖 ＋ 01_offsets.csv
輸出：{case}/02_sheets.csv、{case}/02_exclude.csv

要點：
  - VLM **一次**呼叫，讀出 圖種/樓層/比例/單位/圖框範圍/標題欄/版本線索
  - `orientation` 欄**抄自 01_offsets.csv 的 rotation**（只是紀錄，不重新判斷）
  - 02_sheets 的欄位之後是 plan 的 context 來源，中樞不得自行更改（§6.1）

禁：不要為了提高準確率改成多次呼叫或加迴圈 —— 被動層是確定性的、一次跑完。
禁：不要吃 01_tiles/（未轉正）—— 圖顛倒時 VLM 讀出來的字不能用（裁決 §1）。
"""

from pathlib import Path

# ─────────────────────────────────────────────────────────────
# 樓層：圖上原樣的寫法 → 正規化範圍
# ─────────────────────────────────────────────────────────────
_DIGITS = {"零": 0, "一": 1, "二": 2, "兩": 2, "三": 3, "四": 4, "五": 5,
           "六": 6, "七": 7, "八": 8, "九": 9}
_RANGE_SEPARATORS = ("～", "~", "－", "-", "—", "至", "到")


def _cn_number(text: str):
    """中文數字 → int。支援 十／十一／二十／二十三。看不懂回 None。"""
    t = text.strip()
    if t.isdigit():
        return int(t)
    if not t or any(c not in _DIGITS and c != "十" for c in t):
        return None
    if "十" not in t:
        return _DIGITS.get(t) if len(t) == 1 else None
    head, _, tail = t.partition("十")
    tens = _DIGITS.get(head, 1) if head else 1
    ones = _DIGITS.get(tail, 0) if tail else 0
    return tens * 10 + ones


def parse_floor(text: str):
    """「四樓～十樓」→ (4, 10)；「地下室一樓」→ (-1, -1)；「一樓」→ (1, 1)。

    讀不懂回 (None, None) —— **不要猜**。樓層錯掉會讓整張圖掛到錯的樓層。
    """
    if not text:
        return (None, None)
    t = text.strip()
    for sep in _RANGE_SEPARATORS:
        if sep in t:
            a, b = t.split(sep, 1)
            fa, _ = parse_floor(a)
            fb, _ = parse_floor(b if "樓" in b or "層" in b else b + "樓")
            if fa is not None and fb is not None:
                return (min(fa, fb), max(fa, fb))
            return (None, None)
    sign = -1 if ("地下" in t) else 1
    body = t.replace("地下室", "").replace("地下", "").replace("樓", "").replace("層", "").strip()
    if body in ("屋頂", "頂"):
        return (None, None)                      # 屋頂層沒有數字，交給 note
    n = _cn_number(body)
    return (sign * n, sign * n) if n is not None else (None, None)


# ─────────────────────────────────────────────────────────────
# 分組：一張圖被拆成 N 片，N 不固定
# ─────────────────────────────────────────────────────────────
def group_tiles(readings):
    """依標題欄判讀結果，把片分組成圖。

    規則：**在有圖名或圖號的片切段**。原圖底緣的標題欄只會落在其中一兩片上，
    帶圖名或圖號的那片就是一組的錨點。這自然處理「N 不固定」——
    不需要假設每組四片（規格與實務都沒有這個保證）。

    ★ 圖名與圖號要**任一**即可：實測 79 年案的 p09 標題欄的圖名格是空白的
    （判讀者放大確認過是真空白，不是讀不出），但圖號「3/F-11」清楚；
    p33 則相反 —— 有圖名沒圖號。只認其中一個會漏掉一整張圖。

    readings：[{tile_id, has_title_block, part, drawing_name, drawing_no,
                floor, scale, ...}]，依 tile_id 排序即掃描順序。
    回傳 [{anchor, tiles: [...], drawing_name, ...}]，
    以及 orphans（第一個錨點之前的片，歸屬不明）。
    """
    ordered = sorted(readings, key=lambda r: r["tile_id"])
    groups, orphans, cur = [], [], None
    for r in ordered:
        if r.get("drawing_name") or r.get("drawing_no"):
            cur = {"anchor": r["tile_id"], "meta": r, "tiles": [r]}
            groups.append(cur)
        elif cur is None:
            orphans.append(r)
        else:
            cur["tiles"].append(r)
    return groups, orphans


def assign_cells(group):
    """推 row/col。**只給推得出來的**，推不出來標 ambiguous。

    依據：標題欄橫在原圖**底緣**，所以拍到標題欄的片都在最後一列；
    圖名區在標題欄的右端、簽核區在其左，於是最後一列的左右次序就定了。
    其餘片在上方各列 —— 左右次序無法只從標題欄推得，標 ambiguous 交給 L3。
    """
    tiles = group["tiles"]
    tb = [t for t in tiles if t.get("has_title_block")]
    n_cols = max(1, len(tb))
    n_rows = -(-len(tiles) // n_cols)                 # 無條件進位
    # 左右次序：標題欄由左至右是「修正／簽核欄 → 事務所名 → 工程名稱 → 圖名 → 圖號」，
    # 所以只拍到簽核區的片在左，拍到圖名區（或兩者）的片在右。
    # 實測依據：79 年案 p16 只有簽核區且**最右緣**才切到事務所名的頭兩字「梁慶」，
    # 而 p13 左端是簽核區尾段、右段才是圖名 —— p16 在 p13 左邊。
    order = {"簽核區": 0, "圖名區": 1, "兩者皆有": 1}
    bottom = sorted(tb, key=lambda t: order.get(t.get("part"), 9))
    out = []
    for i, t in enumerate(bottom):
        out.append({"tile_id": t["tile_id"], "row": n_rows - 1, "col": i,
                    "part": t.get("part", "無"), "conf": 0.9, "status": "assigned",
                    "evidence": f"標題欄{t.get('part')}在原圖底緣",
                    "note": ""})
    rest = [t for t in tiles if t not in bottom]
    for i, t in enumerate(rest):
        out.append({"tile_id": t["tile_id"], "row": None, "col": None,
                    "part": "無", "conf": 0.0, "status": "ambiguous",
                    "evidence": "",
                    "note": f"非底列；{n_rows}×{n_cols} 網格中的位置需 L3 內容接續判定"})
    return out, n_rows, n_cols


def run(case_dir: Path) -> None:
    raise NotImplementedError(
        "s02_layout 的 case 層封裝未實作。VLM 判讀那半目前由 workflow 代跑；"
        "確定性的 parse_floor / group_tiles / assign_cells 已可用，見 tests/test_layout.py。"
    )
