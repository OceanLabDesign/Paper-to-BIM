"""tools/arrange.py —— 排圖的純邏輯（提案、覆寫、匯出契約、預覽）

介面在 `tools/studio.py`，這支不開伺服器 —— 排圖的規則要能單獨測、
也要能被批次腳本呼叫，所以跟畫面分開。

原圖是 A1／A2，影印機只能印 A3，所以一張圖被拆成數張。這支負責把散開的片
**排回一張圖**，人確認之後才進辨識。

## 為什麼排序要排在辨識前面

一、人在這裡改的是**拓樸（topology）**：這片屬於哪張圖、在哪一格。
   那是人看得出來的。至於差幾個 px（度量 metric）人看不出來，
   也不該在這裡改 —— 那是 ADR 0011 的 s01c，排在辨識之後。

二、**省錢。** 一個案子上百片，真正要重繪的可能只有其中幾張。
   先排完讓人勾掉不需要的，辨識就只跑該跑的。

## 三個檔案，各一個職責

| 檔 | 誰寫 | 為什麼分開 |
|---|---|---|
| `02_arrange_proposal.json` | AI | **不可變。** 重跑或比對「人改了什麼」都要靠它 |
| `02_arrange_review.json` | 人（本 UI） | 只記覆寫（override），沒動過的片不出現 |
| `02_sheets.csv` / `02_sheet_tiles.csv` | 本 UI 的「確認」 | 契約輸出＝提案＋覆寫，下游只讀這兩支 |

同裁決 §1 保留 `01_tiles/` 原始版的理由：判斷錯了要能重跑，不能就地覆蓋。

## 髒資料會被擋下來

`tile_id` 目前是全案流水號，**加一個 PDF 進來就會全部重編**
（實測：加了第二個 PDF 之後消防圖從 p01 變成 p59，而舊的 02_sheet_tiles.csv
是重編前算的，於是它說 p01 是消防平面圖、實際上 p01 已經變成建築圖的面積表）。
所以提案裡每片都記 `src_pdf` / `src_page`，載入時對不上就整份作廢重排。

"""

import csv
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.dont_write_bytecode = True

import cv2                                                        # noqa: E402
import numpy as np                                                # noqa: E402

from core import fields as F                                      # noqa: E402
from perception import s02_layout as L                            # noqa: E402

THUMB_W = 190
SIDE_ZH = {"top": "上", "right": "右", "bottom": "下", "left": "左"}


def tkey(tid: str):
    """tile_id 的**掃描順序**。

    ⚠ 不能用字串排序：`sorted()` 會把 p102 排在 p11 前面（p1<p10<p100<p11），
    整個分組就跟著錯位。實測踩過 —— S03 被排成 [p102, p11]。
    """
    m = re.search(r"\d+", tid)
    return (int(m.group()) if m else 0, tid)


def now() -> str:
    return datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")


# ── 提案 ──────────────────────────────────────────────────────────────────
def source_map(case: Path) -> dict:
    """片 → 它來自哪個 PDF 的第幾頁。tile_id 不穩定，這個才穩定。"""
    out, n = {}, 0
    try:
        import fitz
    except ImportError:
        return out
    for pdf in sorted((case / "00_raw").glob("*.pdf")):
        cnt = fitz.open(str(pdf)).page_count
        for i in range(cnt):
            out[f"p{n + i + 1:02d}"] = {"src_pdf": pdf.name, "src_page": i + 1}
        n += cnt
    return out


def propose(case: Path) -> dict:
    """從標題欄判讀 ＋ 圖框證據，排出第一版。

    分組規則：**開在標題欄，收在下一個標題欄（含）。**
    標題欄橫在原圖底緣，被拆成 A3 之後這條長帶落在同一張圖的底列上、
    通常橫跨兩片，所以一組的頭尾各有一片帶標題欄。

    ★ 不預設「一張圖四片」——實測本案確實都是 4，但那是量出來的不是假設的
    （79 年案標題欄出現在 p03/p06、p07/p10、p11/p14…，間隔穩定為 3）。
    只認「圖名區開頭、簽核區結尾」會漏掉兩片都被判成「兩者皆有」的組
    （p15/p18、p23/p26 都是），所以改認 has_title_block。

    ⚠ 這只是**提案**。79 年案的排列並不整齊（有的頁本身就是完整 A3、
    有的沒有任何標題欄），所以推不出來的一律丟到待分配，讓人拖。
    """
    read = json.loads((case / "02_titleblock_readings.json").read_text(encoding="utf-8"))
    frames = {}
    fp = case / "01_frames.json"
    if fp.exists():
        frames = json.loads(fp.read_text(encoding="utf-8"))
    src = source_map(case)

    info = {}
    for r in read:
        t = r["tile_id"]
        fr = frames.get(t) or {}
        info[t] = {
            "tile_id": t, "part": r.get("part", "無"),
            "has_tb": bool(r.get("has_title_block")),
            "drawing_name": r.get("drawing_name", ""),
            "drawing_no": r.get("drawing_no", ""),
            "floor_text": r.get("floor_text", ""), "scale": r.get("scale", ""),
            "cut_left": bool(r.get("cut_left")), "cut_right": bool(r.get("cut_right")),
            "cut_text": r.get("cut_text", ""),
            "outer": [s for s in ("top", "right", "bottom", "left") if fr.get(s)],
            **src.get(t, {"src_pdf": "", "src_page": 0}),
        }

    order = sorted(info, key=tkey)
    sheets, cur, tray = [], None, []
    for t in order:
        i = info[t]
        if i["has_tb"] and cur is None:            # 標題欄開一組
            cur = {"sheet_id": f"S{len(sheets) + 1:02d}", "tiles": [t],
                   "drawing_name": i["drawing_name"], "drawing_no": i["drawing_no"],
                   "floor_text": i["floor_text"], "scale": i["scale"], "skip": False}
            sheets.append(cur)
        elif cur is not None:
            cur["tiles"].append(t)
            for k in ("drawing_name", "drawing_no", "floor_text", "scale"):
                cur[k] = cur[k] or i[k]            # 圖名可能落在後面那片上
            if i["has_tb"]:                        # 下一個標題欄收一組
                cur = None
        else:
            tray.append(t)                         # 第一個標題欄之前，歸屬不明

    for s in sheets:
        n = len(s["tiles"])
        s["cols"] = max(1, min(n, 2 if n <= 4 else 3))
        s["rows"] = -(-n // s["cols"])
        s["cells"], left = place_cells(s["tiles"], info, s["rows"], s["cols"])
        tray += left
        s["tiles"] = sorted(s["cells"].values())

    return {"case": case.name, "made": now(), "sheets": sheets,
            "tray": tray, "info": info}


def place_cells(tiles, info, rows, cols):
    """把片放進網格。**硬約束先釘，釘不住的才按掃描順序填空位。**

    兩條硬約束，都不是猜的：

    1. **帶標題欄的片在最底列。** 標題欄橫在圖框底緣是台灣製圖慣例；
       而且底列的左右次序也定了 —— 標題欄由左到右是
       「簽核區 → 事務所名 → 工程名稱 → 圖名 → 圖號」，
       所以只拍到簽核區的在左、拍到圖名／圖號的在右。
    2. **有圖框外緣的片貼那一側。** 有上框就在第 0 列，有左框就在第 0 行。

    剩下的按掃描順序填 —— 那是猜的，所以擺完就交給人拖。
    回傳 (cells, 放不下的片)。
    """
    cells, placed = {}, set()

    def put(t, r, c):
        if 0 <= r < rows and 0 <= c < cols and f"{r},{c}" not in cells:
            cells[f"{r},{c}"] = t
            placed.add(t)
            return True
        return False

    # 底列由左到右：先按標題欄的段落（簽核區在左），同段落時用**反向掃描順序** ——
    # ADR 0009 在本案量到的掃描次序是 右下 → 右上 → 左上 → 左下，
    # 所以組裡越晚掃到的越靠左。兩片都被判成「兩者皆有」時只能靠這條。
    tb = sorted((t for t in tiles if info[t]["has_tb"]),
                key=lambda t: (0 if info[t]["part"] == "簽核區" else
                               2 if info[t]["part"] == "圖名區" else 1,
                               [-i for i, x in enumerate(tiles) if x == t][0]))
    for c, t in enumerate(tb):                       # 約束 1
        put(t, rows - 1, c)

    for t in tiles:                                  # 約束 2：兩軸都釘得住
        if t in placed:
            continue
        o = info[t]["outer"]
        r = 0 if "top" in o else (rows - 1 if "bottom" in o else None)
        c = 0 if "left" in o else (cols - 1 if "right" in o else None)
        if r is not None and c is not None:
            put(t, r, c)

    for t in tiles:                                  # 約束 2：只釘得住一軸
        if t in placed:
            continue
        o = info[t]["outer"]
        r = 0 if "top" in o else (rows - 1 if "bottom" in o else None)
        c = 0 if "left" in o else (cols - 1 if "right" in o else None)
        if r is not None:
            for cc in range(cols):
                if put(t, r, cc):
                    break
        elif c is not None:
            for rr in range(rows):
                if put(t, rr, c):
                    break

    for t in tiles:                                  # 其餘：掃描順序填空位
        if t in placed:
            continue
        for rr in range(rows):
            for cc in range(cols):
                if put(t, rr, cc):
                    break
            if t in placed:
                break
    return cells, [t for t in tiles if t not in placed]


# ── 狀態 ──────────────────────────────────────────────────────────────────
class State:
    def __init__(self, case: Path):
        self.case = case
        self.pf = case / "02_arrange_proposal.json"
        self.rf = case / "02_arrange_review.json"
        if not self.pf.exists():
            self.pf.write_text(json.dumps(propose(case), ensure_ascii=False, indent=1),
                               encoding="utf-8")
        self.p = json.loads(self.pf.read_text(encoding="utf-8"))
        self._check_stale()
        self.r = (json.loads(self.rf.read_text(encoding="utf-8"))
                  if self.rf.exists() else {"cells": {}, "sheets": {}, "log": []})

    def _check_stale(self):
        """提案裡每片的 src_pdf/src_page 要對得上現在的 PDF，否則整份作廢。"""
        cur = source_map(self.case)
        if not cur:
            return
        bad = [t for t, i in self.p["info"].items()
               if i.get("src_pdf") and cur.get(t, {}).get("src_pdf") != i["src_pdf"]]
        if bad:
            raise SystemExit(
                f"✗ 提案過期：{len(bad)} 片的來源 PDF 對不上（例如 {bad[:3]}）。\n"
                f"  多半是又加了 PDF 讓 tile_id 重編。刪掉 {self.pf.name} 重排。")

    def save(self):
        self.r["updated"] = now()
        self.rf.write_text(json.dumps(self.r, ensure_ascii=False, indent=1),
                           encoding="utf-8")

    def view(self) -> dict:
        """提案套上人的覆寫。UI 與匯出都用這份。

        先算出「每片該在哪」再一次填格，**不要邊掃邊改格子** ——
        那樣把片拖到已占用的格子時，原本那片會憑空消失（既不在格子裡也不在待分配）。
        現在的作法下，被擠掉的片自然回到待分配區。
        """
        sheets = [{**s, **self.r["sheets"].get(s["sheet_id"], {}), "cells": {}}
                  for s in self.p["sheets"] + self.r.get("added", [])]
        by_id = {s["sheet_id"]: s for s in sheets}

        assign = {}
        for s0 in self.p["sheets"] + self.r.get("added", []):
            for k, t in s0.get("cells", {}).items():
                if t not in self.r["cells"]:
                    r, c = k.split(",")
                    assign[t] = (s0["sheet_id"], int(r), int(c))
        for t, dest in self.r["cells"].items():        # 覆寫；後到的贏
            if dest:
                assign[t] = (dest["sheet_id"], int(dest["r"]), int(dest["c"]))

        for t, (sid, r, c) in assign.items():
            s = by_id.get(sid)
            if s is not None:
                s["cells"][f"{r},{c}"] = t
        for s in sheets:                               # 格子不能被網格切掉
            for k in s["cells"]:
                r, c = (int(x) for x in k.split(","))
                s["rows"] = max(s.get("rows", 1), r + 1)
                s["cols"] = max(s.get("cols", 1), c + 1)
            s["tiles"] = sorted(s["cells"].values())

        placed = {t for s in sheets for t in s["cells"].values()}
        tray = [t for t in sorted(self.p["info"], key=tkey) if t not in placed]
        return {"sheets": sheets, "tray": tray, "info": self.p["info"]}


# ── 匯出契約 ──────────────────────────────────────────────────────────────
def commit(st: State) -> dict:
    v = st.view()
    info = v["info"]
    keep = [s for s in v["sheets"] if not s.get("skip") and s["cells"]]
    rows_t, rows_s = [], []
    for s in keep:
        for k, t in sorted(s["cells"].items()):
            r, c = k.split(",")
            manual = t in st.r["cells"]
            rows_t.append({
                "tile_id": t, "sheet_id": s["sheet_id"], "row": r, "col": c,
                "part": info[t]["part"],
                "evidence": ("人工排定" if manual else
                             (f"標題欄{info[t]['part']}"
                              + (f"；殘字「{info[t]['cut_text']}」"
                                 if info[t].get("cut_text") else "")
                              + (f"；外緣 {'/'.join(SIDE_ZH[x] for x in info[t]['outer'])}"
                                 if info[t]["outer"] else ""))),
                "conf": 1.0 if manual else (0.9 if info[t]["has_tb"] else 0.5),
                "status": "assigned", "note": "",
            })
        fa, fb = L.parse_floor(s.get("floor_text", ""))
        rows_s.append({
            "sheet_id": s["sheet_id"], "kind": "", "drawing_floor": s.get("floor_text", ""),
            "floor_from": "" if fa is None else fa, "floor_to": "" if fb is None else fb,
            "scale": s.get("scale", ""), "unit": "", "orientation": "",
            "drawing_no": s.get("drawing_no", ""), "drawing_name": s.get("drawing_name", ""),
            "tile_count": len(s["cells"]), "frame_wkt": "", "title_block_wkt": "",
            "version_hint": "", "note": f"{s['rows']}×{s['cols']} 網格；人工確認",
        })
    for name, fields, rows in (("02_sheet_tiles.csv", F.SHEET_TILES, rows_t),
                               ("02_sheets.csv", F.SHEETS, rows_s)):
        with (st.case / name).open("w", newline="", encoding="utf-8") as fh:
            w = csv.DictWriter(fh, fieldnames=fields)
            w.writeheader()
            w.writerows([{k: r.get(k, "") for k in fields} for r in rows])
    skipped = [s["sheet_id"] for s in v["sheets"] if s.get("skip")]
    return {"sheets": len(keep), "tiles": len(rows_t),
            "skipped": skipped, "tray": len(v["tray"])}


# ── 縮圖 ──────────────────────────────────────────────────────────────────
_TH = {}


def thumb(case: Path, tid: str) -> bytes:
    if tid not in _TH:
        g = cv2.imread(str(case / "01_tiles_upright" / f"{tid}.png"), 0)
        g = cv2.normalize(g, None, 0, 255, cv2.NORM_MINMAX)
        h = int(THUMB_W * g.shape[0] / g.shape[1])
        _TH[tid] = cv2.imencode(".png", cv2.resize(g, (THUMB_W, h),
                                interpolation=cv2.INTER_AREA))[1].tobytes()
    return _TH[tid]


def preview(case: Path, sheet: dict, scale=0.085) -> bytes:
    """把一張圖的各片依格子**直接對接**成一張，給人一眼判斷排得對不對。

    ⚠ **這不是真的拼圖，是對接預覽。** 相鄰的 A3 之間有重疊
    （實測 79 年案同一個圖形會同時出現在左片右緣與右片左緣），
    直接對接會讓重疊的內容重複出現。扣掉重疊要有每片的 (dx, dy)，
    那是 s01c 的度量層、排在辨識之後（ADR 0011）。

    這裡只需要判斷「拓樸對不對」—— 標題欄接不接得起來、內容大方向連不連得上。
    """
    cells = sheet["cells"]
    if not cells:
        return b""
    ims = {}
    for k, t in cells.items():
        g = cv2.imread(str(case / "01_tiles_upright" / f"{t}.png"), 0)
        g = cv2.normalize(g, None, 0, 255, cv2.NORM_MINMAX)
        ims[k] = cv2.resize(g, (0, 0), fx=scale, fy=scale,
                            interpolation=cv2.INTER_AREA)
    h, w = next(iter(ims.values())).shape
    R, C = sheet["rows"], sheet["cols"]
    canvas = np.full((h * R, w * C), 255, np.uint8)
    for k, im in ims.items():
        r, c = (int(x) for x in k.split(","))
        canvas[r * h:r * h + im.shape[0], c * w:c * w + im.shape[1]] = im
    canvas = cv2.cvtColor(canvas, cv2.COLOR_GRAY2BGR)
    for r in range(1, R):
        cv2.line(canvas, (0, r * h), (w * C, r * h), (0, 0, 255), 1)
    for c in range(1, C):
        cv2.line(canvas, (c * w, 0), (c * w, h * R), (0, 0, 255), 1)
    return cv2.imencode(".png", canvas)[1].tobytes()
