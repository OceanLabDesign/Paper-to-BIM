"""tools/desktop.py —— Paper-to-BIM 工作站（原生視窗，不用瀏覽器）

    python3 tools/desktop.py                # 開視窗
    python3 tools/desktop.py --selftest     # 不開視窗，跑一輪資料與繪圖的檢查

**這支是主程式。** 選案 → 排圖 → 校對 → 成果 → 進度。

只用標準函式庫的 tkinter，**沒有新增任何相依**。控件在 `tools/win95.py`，
規則在 `tools/arrange.py`（排圖）與 `tools/review.py`（校對）——
規則不放進畫面，是為了能單獨測、也能被批次腳本呼叫。

## macOS 上踩過的坑（都寫在動它的地方）

1. **幽靈影像會毒化命中測試。** 拖曳時跟著游標的 Toplevel 會讓
   `winfo_containing()` 回傳幽靈自己（它也屬於同一個應用程式），`-alpha`
   跟 `-transparent` 都無效 —— 那是視窗階層查詢，不是像素查詢。
   解法是幽靈永遠放在游標 **+16,+16**，讓熱點落在它左上角外面。
2. **Tk 事件不冒泡。** 只在卡片 Frame 上 bind，點在裡面的 Label(image=) 上
   收不到任何事件。要遞迴綁整棵子樹。
3. **PhotoImage 會被 GC，而且症狀陰險** —— 參考消失後畫面變空白，但
   `winfo_width/height` 仍是原尺寸，用幾何量測完全偵測不到。
   所以縮圖一律存在 `self.imgs` 這個獨立於畫面生命週期的 dict，
   **不要存在控件屬性上**（重繪會 destroy 控件，參考跟著死）。
4. **不要在控件上自訂 `_w` 屬性** —— 那是 Tk 內部用的，會炸 TypeError。
   本檔一律用 `pb_` 前綴。
5. **Canvas 的 find_closest 是陷阱**，滑鼠離所有框十萬八千里它也回一個 item。
   要用 `find_overlapping` 再用 tag 過濾。而且空心矩形只有邊線算命中，
   所以框都給 `fill` + `stipple`。
6. **macOS 的滾輪 delta 是「格數」（±1）**，不是 Windows 的 ±120；
   而且 Canvas 沒有任何內建滾輪綁定，一定要自己 bind。

來源：2026-08-23 用 CoreGraphics 讀回真實像素做的實測。
"""

import os
import sys
import traceback
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if not getattr(sys, "frozen", False):
    sys.path.insert(0, str(ROOT))
sys.dont_write_bytecode = True


def _fix_std_streams():
    """`--windowed` 打包之後 **Windows 上 `sys.stdout` 是 None**，`print()` 會丟
    AttributeError —— 連 `traceback.print_exc()` 都印不出來，使用者只看到程式無聲消失。

    所以沒有主控台時把兩條串流導到記錄檔。這不只是為了 CI：
    使用者回報「按了沒反應」時，這個檔是唯一的線索。
    """
    if sys.stdout is not None and sys.stderr is not None:
        return None
    log = Path(os.environ.get("TMPDIR") or os.environ.get("TEMP") or "/tmp") / \
        "paper-to-bim.log"
    try:
        fh = open(log, "a", encoding="utf-8", buffering=1)
    except OSError:
        return None
    if sys.stdout is None:
        sys.stdout = fh
    if sys.stderr is None:
        sys.stderr = fh
    return log


LOG_PATH = _fix_std_streams()


def app_dir() -> Path:
    """使用者資料的基準目錄。

    ⚠ **凍結（frozen）之後不能用 `__file__`** —— 它會指到 bundle 內部（唯讀，
    而且使用者根本看不到）。改用執行檔旁邊；macOS 的 .app 還要再往外跳三層，
    因為執行檔實際在 `Foo.app/Contents/MacOS/Foo`。

    順序：環境變數 PAPER_TO_BIM_HOME → 執行檔旁邊 → ~/Documents/Paper-to-BIM
    """
    env = os.environ.get("PAPER_TO_BIM_HOME")
    if env:
        return Path(env).expanduser()
    if not getattr(sys, "frozen", False):
        return ROOT
    exe = Path(sys.executable).resolve()
    if exe.parent.name == "MacOS" and exe.parent.parent.name == "Contents":
        base = exe.parent.parent.parent.parent      # Foo.app 的同層
    else:
        base = exe.parent
    if (base / "cases").is_dir():
        return base
    home = Path.home() / "Documents" / "Paper-to-BIM"
    (home / "cases").mkdir(parents=True, exist_ok=True)
    return home

import tkinter as tk                                              # noqa: E402
from tkinter import ttk                                           # noqa: E402

import cv2                                                        # noqa: E402
import numpy as np                                                # noqa: E402

from tools import arrange as A                                    # noqa: E402
from tools import review as R                                     # noqa: E402
from tools import win95 as W                                      # noqa: E402

CASES = app_dir() / "cases"
TABS = ("選案", "排圖", "校對", "成果", "進度")
THUMB_W = 150
REV_SCALE = 0.30

BADGES = (
    ("開工", "把第一片拖到正確位置", lambda s: s["moved"] >= 1),
    ("清空待分配", "每一片都有歸屬或被刪掉", lambda s: s["tray"] == 0),
    ("策展人", "刪掉至少一片沒用的掃描", lambda s: s["deleted"] >= 1),
    ("抓重點", "勾掉至少一張不需要辨識的圖", lambda s: s["skipped"] >= 1),
    ("圖圖有名", "每張圖都有圖名", lambda s: s["unnamed"] == 0 and s["sheets"] > 0),
    ("全員就位", "所有圖都排滿格子", lambda s: s["holes"] == 0 and s["sheets"] > 0),
    ("上了座標", "跑完度量層，過半的片有實測錨點",
     lambda s: s["tier_good"] >= max(1, s["placed"] // 2)),
    ("說了算", "校對確認第一個元素（訓練資料的第一筆）", lambda s: s["reviewed"] >= 1),
    ("教練", "累積 50 個人工確認的框", lambda s: s["reviewed"] >= 50),
)

BOX_COLOR = {"pending": "#c05028", "confirmed": "#008000",
             "rejected": "#a00000", "edited": "#d88000"}


def png_photo(data: bytes) -> tk.PhotoImage:
    """PNG bytes → PhotoImage。

    Tk 8.6 的 PhotoImage 直接吃 PNG 的 raw bytes（PPM 才只吃 raw、不吃 base64）。
    """
    return tk.PhotoImage(data=data)


def case_list():
    if not CASES.exists():
        return []
    return sorted(d.name for d in CASES.iterdir()
                  if d.is_dir() and not d.name.startswith("_"))


def bind_tree(widget, seq, fn):
    """Tk 事件不冒泡，要自己綁整棵子樹（見檔頭坑 2）。"""
    widget.bind(seq, fn)
    for c in widget.winfo_children():
        bind_tree(c, seq, fn)


# ─────────────────────────────────────────────────────────────────────────
class Model:
    """一個案子的資料。畫面不直接碰 arrange/review，都經過這裡。"""

    def __init__(self, name):
        self.name = name
        self.case = CASES / name
        self.st = A.State(self.case)
        self.st.r.setdefault("deleted", [])
        self._rev = {}

    def review(self, tile):
        if tile not in self._rev:
            self._rev[tile] = R.Review(self.case, tile)
        return self._rev[tile]

    def reviewable(self):
        return R.reviewable(self.case)

    def placement(self):
        import csv
        f = self.case / "01_placement.csv"
        if not f.exists():
            return {}
        return {r["tile_id"]: r for r in csv.DictReader(f.open(encoding="utf-8"))}

    def view(self):
        v = self.st.view()
        dead = set(self.st.r["deleted"])
        for s in v["sheets"]:
            s["cells"] = {k: t for k, t in s["cells"].items() if t not in dead}
            s["tiles"] = sorted(s["cells"].values())
        v["tray"] = [t for t in v["tray"] if t not in dead]
        v["deleted"] = sorted(dead, key=A.tkey)
        return v

    def stats(self):
        v = self.view()
        pl = self.placement()
        sheets = [s for s in v["sheets"] if s["cells"]]
        s = {
            "total": len(v["info"]),
            "placed": sum(len(x["cells"]) for x in sheets),
            "tray": len(v["tray"]), "deleted": len(v["deleted"]),
            "sheets": len(sheets),
            "skipped": sum(1 for x in v["sheets"] if x.get("skip")),
            "moved": len(self.st.r.get("cells", {})),
            "unnamed": sum(1 for x in sheets if not x.get("drawing_name")),
            "holes": sum(x["rows"] * x["cols"] - len(x["cells"]) for x in sheets),
            "tier_good": sum(1 for r in pl.values() if r["tier"] in ("2", "4")),
            "reviewed": sum(self.review(t).stats()["labels"]
                            for t in self.reviewable()),
        }
        s["badges"] = [{"name": n, "desc": d, "got": bool(f(s))}
                       for n, d, f in BADGES]
        s["pct"] = round(100 * (s["placed"] + s["deleted"]) / max(1, s["total"]))
        return s

    # 動作
    def move(self, tile, dest):
        self.st.r["cells"][tile] = dest
        self.st.save()

    def set_sheet(self, sid, field, value):
        o = self.st.r["sheets"].setdefault(sid, {})
        if field == "resize":
            base = next(x for x in self.view()["sheets"] if x["sheet_id"] == sid)
            o["rows"] = max(1, base["rows"] + value[0])
            o["cols"] = max(1, base["cols"] + value[1])
        else:
            o[field] = value
        self.st.save()

    def del_tile(self, tile):
        if tile not in self.st.r["deleted"]:
            self.st.r["deleted"].append(tile)
        self.st.r["cells"][tile] = None
        self.st.save()

    def undelete(self):
        self.st.r["deleted"] = []
        self.st.save()

    def del_sheet(self, sid):
        for x in self.st.p["sheets"] + self.st.r.get("added", []):
            if x["sheet_id"] == sid:
                for t in x.get("cells", {}).values():
                    self.st.r["cells"][t] = None
        for t, c in list(self.st.r["cells"].items()):
            if c and c.get("sheet_id") == sid:
                self.st.r["cells"][t] = None
        o = self.st.r["sheets"].setdefault(sid, {})
        o["rows"] = o["cols"] = 0
        self.st.save()

    def new_sheet(self):
        add = self.st.r.setdefault("added", [])
        add.append({"sheet_id": f"X{len(add) + 1:02d}", "cells": {}, "rows": 2,
                    "cols": 2, "drawing_name": "", "drawing_no": "",
                    "floor_text": "", "scale": "", "skip": False})
        self.st.save()

    def commit(self):
        return A.commit(self.st)


# ─────────────────────────────────────────────────────────────────────────
class Desktop:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("Paper-to-BIM 工作站")
        self.root.geometry("1280x820")
        self.root.configure(bg=W.FACE)
        W.install_clam(self.root)
        self.model = None
        self.imgs = {}          # 縮圖的中央參考（見檔頭坑 3）
        self.sel_tile = None
        self.sel_el = None
        self.rev_tile = None
        self.rev_view = "orig"
        self.page = 0
        self.drag = None
        self.job = W.ThreadJob(self.root)

        outer = W.Bevel(self.root, kind="raised", width=2, bg=W.FACE)
        outer.pack(fill="both", expand=True, padx=4, pady=4)
        body = outer.inner

        self.tabs = W.Win95Tabs(body, TABS)
        self.tabs.pack(fill="both", expand=True, padx=4, pady=(4, 2))
        for i, tab in enumerate(self.tabs._tabs):
            for wid in (tab,) + tuple(tab.winfo_children()):
                wid.bind("<Button-1>", lambda _e, k=i: self.go(k), add="+")

        self.status = W.Win95StatusBar(body, widths=(0, 230, 150))
        self.status.pack(fill="x", padx=4, pady=(0, 4))
        self.status.set(0, "請先選一個案子")

        self.root.protocol("WM_DELETE_WINDOW", self.close)
        self.go(0)

    # ── 導覽 ──────────────────────────────────────────────────────────
    def go(self, i):
        if i > 0 and self.model is None:
            self.tabs.select(0)
            self.status.set(0, "請先選一個案子")
            i = 0
        self.tabs.select(i)
        page = self.tabs.pages[i]
        for c in page.winfo_children():
            c.destroy()
        (self.pane_case, self.pane_arrange, self.pane_review,
         self.pane_book, self.pane_prog)[i](page)
        self.refresh_status()

    def refresh_status(self):
        if not self.model:
            return
        s = self.model.stats()
        self.status.set(0, self.model.name)
        self.status.set(1, f"已排 {s['placed']}/{s['total']}　"
                           f"待分配 {s['tray']}　刪 {s['deleted']}")
        self.status.set(2, f"成就 {sum(1 for b in s['badges'] if b['got'])}"
                           f"/{len(s['badges'])}")

    def close(self):
        self.job.shutdown()
        self.root.destroy()

    def run(self):
        self.root.mainloop()

    # ── 選案 ──────────────────────────────────────────────────────────
    def pane_case(self, p):
        tk.Label(p, text="選擇案件資料夾", bg=W.FACE, font=W.ui_font(12, True)
                 ).pack(anchor="w", padx=10, pady=(10, 4))
        box = W.Bevel(p, kind="sunken", width=2, bg=W.FIELD)
        box.pack(fill="both", expand=False, padx=10)
        lb = tk.Listbox(box.inner, bg=W.FIELD, fg=W.TEXT, font=W.ui_font(12),
                        bd=0, highlightthickness=0, height=8,
                        selectbackground=W.NAVY, selectforeground=W.WHITE)
        lb.pack(fill="both", expand=True)
        cases = case_list()
        for c in cases:
            n = len(list((CASES / c / "01_tiles_upright").glob("*.png")))
            lb.insert("end", f"  {c}    （{n} 片）")
        if not cases:
            lb.insert("end", "  cases/ 底下沒有案件資料夾")

        def open_case(_e=None):
            if not cases or not lb.curselection():
                return
            self.model = Model(cases[lb.curselection()[0]])
            self.rev_tile = None
            self.imgs.clear()
            self.root.title(f"Paper-to-BIM 工作站 － {self.model.name}")
            self.go(1)

        lb.bind("<Double-Button-1>", open_case)
        row = tk.Frame(p, bg=W.FACE)
        row.pack(anchor="w", padx=10, pady=8)
        W.Win95Button(row, text="開啟", command=open_case, width=90).pack(side="left")
        W.Win95Button(row, text="換資料夾…", command=self.act_pick_dir,
                      width=110).pack(side="left", padx=4)
        tk.Label(row, text="（或在清單上按兩下）", bg=W.FACE, fg=W.GRAY,
                 font=W.ui_font(11)).pack(side="left", padx=8)
        tk.Label(p, text=f"目前：{CASES}", bg=W.FACE, fg=W.GRAY,
                 font=W.ui_font(10)).pack(anchor="w", padx=10)

        info = W.Bevel(p, kind="sunken", width=1, bg="#ffffe1")
        info.pack(fill="x", padx=10, pady=(6, 10))
        tk.Label(info.inner, justify="left", bg="#ffffe1", font=W.ui_font(11),
                 text="① 排圖：AI 先排一次，你拖到正確位置、刪掉不要的\n"
                      "② 校對：逐條裁定 AI 的判讀，確認過的框才會進訓練集\n"
                      "③ 成果：一頁一張圖翻著看\n"
                      "先排完可以只辨識真正要的圖 —— 省時間也省錢"
                 ).pack(anchor="w", padx=8, pady=6)

    def act_pick_dir(self):
        """讓使用者指定 cases/ 在哪。做成執行檔之後這是必要的 ——
        使用者的案件不會、也不該放在程式包裡面。"""
        from tkinter import filedialog
        global CASES
        d = filedialog.askdirectory(title="選擇存放案件的資料夾（裡面要有 cases/）")
        if not d:
            return
        d = Path(d)
        CASES = d / "cases" if (d / "cases").is_dir() else d
        self.model = None
        self.imgs.clear()
        self.go(0)

    # ── 排圖 ──────────────────────────────────────────────────────────
    def thumb(self, tile, width=THUMB_W):
        """縮圖。**磁碟快取是必要的，不是最佳化。**

        原片是 4960×3507 的 PNG，解一張約 0.15 秒；排圖畫面上有一百張，
        第一次建畫面實測 14.6 秒 —— 那不是「有點慢」，是每次拖曳完重繪都要再等一次。
        快取寫進案件資料夾的 `.thumbs/`（不進版控），之後開啟都是毫秒級。
        """
        key = (tile, width)
        if key in self.imgs:
            return self.imgs[key]
        cache = self.model.case / ".thumbs"
        cache.mkdir(exist_ok=True)
        f = cache / f"{tile}_{width}.png"
        if f.exists():
            png = f.read_bytes()
        else:
            g = cv2.imread(str(self.model.case / "01_tiles_upright" / f"{tile}.png"), 0)
            g = cv2.normalize(g, None, 0, 255, cv2.NORM_MINMAX)
            h = max(1, int(width * g.shape[0] / g.shape[1]))
            png = cv2.imencode(".png", cv2.resize(g, (width, h),
                               interpolation=cv2.INTER_AREA))[1].tobytes()
            f.write_bytes(png)
        self.imgs[key] = png_photo(png)
        return self.imgs[key]

    def card(self, parent, tile, width=THUMB_W):
        info = self.v["info"].get(tile, {})
        f = W.Bevel(parent, kind="raised", width=1, bg=W.FACE)
        f.pb_tile = tile
        lab = tk.Label(f.inner, image=self.thumb(tile, width), bd=0,
                       highlightthickness=0, bg=W.FACE)
        lab.pack()
        tk.Label(f.inner, text=tile + ("　" + info.get("part", "")
                                       if info.get("has_tb") else ""),
                 bg=W.NAVY if info.get("has_tb") else W.FACE,
                 fg=W.WHITE if info.get("has_tb") else W.TEXT,
                 font=W.ui_font(10), anchor="w").pack(fill="x")
        bind_tree(f, "<ButtonPress-1>", lambda e, t=tile: self.drag_start(e, t))
        bind_tree(f, "<B1-Motion>", self.drag_move)
        bind_tree(f, "<ButtonRelease-1>", self.drag_end)
        return f

    def drag_start(self, _e, tile):
        self.sel_tile = tile
        self.drag = {"tile": tile, "ghost": None}

    def drag_move(self, e):
        if not self.drag:
            return
        g = self.drag["ghost"]
        if g is None:
            g = tk.Toplevel(self.root)
            g.overrideredirect(True)
            try:
                g.attributes("-alpha", 0.75)
            except tk.TclError:
                pass
            tk.Label(g, image=self.thumb(self.drag["tile"], 90), bd=2,
                     relief="solid", bg=W.NAVY).pack()
            self.drag["ghost"] = g
        # ⚠ 幽靈一定要偏離游標熱點，否則 winfo_containing 會回傳幽靈自己（坑 1）
        g.geometry(f"+{e.x_root + 16}+{e.y_root + 16}")

    def drag_end(self, e):
        d, self.drag = self.drag, None
        if not d:
            return
        if d["ghost"] is not None:
            d["ghost"].destroy()
        w = self.root.winfo_containing(e.x_root, e.y_root)
        dest = None
        while w is not None:
            if getattr(w, "pb_cell", None) is not None:
                dest = w.pb_cell
                break
            if getattr(w, "pb_tray", False):
                dest = "tray"
                break
            w = getattr(w, "master", None)
        if dest is None:
            self.refresh_arrange()
            return
        self.model.move(d["tile"], None if dest == "tray" else dest)
        self.refresh_arrange()

    def pane_arrange(self, p):
        self.arrange_root = p
        self.refresh_arrange()

    def refresh_arrange(self):
        p = self.arrange_root
        for c in p.winfo_children():
            c.destroy()
        self.v = self.model.view()

        right = tk.Frame(p, bg=W.FACE, width=190)
        right.pack(side="right", fill="y", padx=(4, 6), pady=6)
        right.pack_propagate(False)
        tk.Label(right, text=f"待分配　{len(self.v['tray'])} 片", bg=W.FACE,
                 font=W.ui_font(11, True)).pack(anchor="w")
        tray = W.Bevel(right, kind="sunken", width=2, bg=W.FIELD)
        tray.pack(fill="both", expand=True, pady=2)
        tray.inner.pb_tray = True
        tcan = tk.Canvas(tray.inner, bg=W.FIELD, bd=0, highlightthickness=0)
        tcan.pack(side="left", fill="both", expand=True)
        tsb = ttk.Scrollbar(tray.inner, orient="vertical", command=tcan.yview)
        tsb.pack(side="right", fill="y")
        tcan.configure(yscrollcommand=tsb.set, yscrollincrement=20)
        tin = tk.Frame(tcan, bg=W.FIELD)
        tin.pb_tray = True
        tcan.create_window(0, 0, window=tin, anchor="nw")
        tcan.pb_tray = True
        for t in self.v["tray"]:
            self.card(tin, t, 150).pack(pady=2)
        tin.update_idletasks()
        tcan.configure(scrollregion=tcan.bbox("all"))
        W.wheel_bind(tcan)

        btns = tk.Frame(right, bg=W.FACE)
        btns.pack(fill="x", pady=(4, 0))
        for txt, fn in (("新增圖", self.act_new_sheet),
                        ("刪除選取的片", self.act_del_tile),
                        ("還原刪除", self.act_undelete),
                        ("✔ 確認排列", self.act_commit)):
            W.Win95Button(btns, text=txt, command=fn, width=180).pack(pady=1)

        left = W.Bevel(p, kind="sunken", width=2, bg=W.FACE)
        left.pack(side="left", fill="both", expand=True, padx=(6, 0), pady=6)
        can = tk.Canvas(left.inner, bg=W.FACE, bd=0, highlightthickness=0)
        can.pack(side="left", fill="both", expand=True)
        sb = ttk.Scrollbar(left.inner, orient="vertical", command=can.yview)
        sb.pack(side="right", fill="y")
        can.configure(yscrollcommand=sb.set, yscrollincrement=24)
        board = tk.Frame(can, bg=W.FACE)
        can.create_window(0, 0, window=board, anchor="nw")

        for s in self.v["sheets"]:
            if not s["cells"] and not s.get("rows"):
                continue
            self.sheet_block(board, s)
        board.update_idletasks()
        can.configure(scrollregion=can.bbox("all"))
        W.wheel_bind(can)
        self.refresh_status()

    def sheet_block(self, parent, s):
        blk = W.Bevel(parent, kind="raised", width=2, bg=W.FACE)
        blk.pack(fill="x", padx=6, pady=4)
        head = tk.Frame(blk.inner, bg=W.FACE)
        head.pack(fill="x", padx=4, pady=3)
        tk.Label(head, text=s["sheet_id"], bg=W.FACE, font=W.ui_font(12, True)
                 ).pack(side="left")

        def entry(field, val, width):
            b = W.Bevel(head, kind="sunken", width=2, bg=W.FIELD)
            b.pack(side="left", padx=3)
            e = tk.Entry(b.inner, bg=W.FIELD, fg=W.TEXT, font=W.ui_font(11),
                         bd=0, highlightthickness=0, width=width)
            e.insert(0, val or "")
            e.pack()
            e.bind("<FocusOut>", lambda _e: self.model.set_sheet(
                s["sheet_id"], field, e.get()))
            e.bind("<Return>", lambda _e: (self.model.set_sheet(
                s["sheet_id"], field, e.get()), self.refresh_arrange()))
            return e

        entry("drawing_name", s.get("drawing_name"), 26)
        entry("floor_text", s.get("floor_text"), 8)
        for txt, fn in (("＋列", lambda: self.act_resize(s["sheet_id"], 1, 0)),
                        ("＋行", lambda: self.act_resize(s["sheet_id"], 0, 1)),
                        ("跳過" if not s.get("skip") else "已跳過",
                         lambda: self.act_skip(s["sheet_id"], not s.get("skip"))),
                        ("刪圖", lambda: self.act_del_sheet(s["sheet_id"]))):
            W.Win95Button(head, text=txt, command=fn, width=54).pack(side="left", padx=1)
        tk.Label(head, text=f"{s['rows']}×{s['cols']}　{len(s['cells'])} 片",
                 bg=W.FACE, fg=W.GRAY, font=W.ui_font(11)).pack(side="left", padx=6)

        grid = tk.Frame(blk.inner, bg=W.FACE)
        grid.pack(anchor="w", padx=4, pady=(0, 4))
        for r in range(s["rows"]):
            for c in range(s["cols"]):
                cell = W.Bevel(grid, kind="sunken", width=1, bg=W.FIELD)
                cell.grid(row=r, column=c, padx=2, pady=2)
                cell.inner.configure(width=THUMB_W + 4, height=118)
                cell.inner.grid_propagate(False)
                cell.inner.pack_propagate(False)
                # ⚠ 屬性名不能叫 _w（Tk 內部用），一律 pb_ 前綴（坑 4）
                cell.pb_cell = {"sheet_id": s["sheet_id"], "r": r, "c": c}
                cell.inner.pb_cell = cell.pb_cell
                t = s["cells"].get(f"{r},{c}")
                if t:
                    card = self.card(cell.inner, t)
                    card.pack()
                    card.pb_cell = cell.pb_cell

    def act_resize(self, sid, dr, dc):
        self.model.set_sheet(sid, "resize", [dr, dc]); self.refresh_arrange()

    def act_skip(self, sid, v):
        self.model.set_sheet(sid, "skip", v); self.refresh_arrange()

    def act_del_sheet(self, sid):
        self.model.del_sheet(sid); self.refresh_arrange()

    def act_new_sheet(self):
        self.model.new_sheet(); self.refresh_arrange()

    def act_del_tile(self):
        if self.sel_tile:
            self.model.del_tile(self.sel_tile)
            self.sel_tile = None
            self.refresh_arrange()

    def act_undelete(self):
        self.model.undelete(); self.refresh_arrange()

    def act_commit(self):
        r = self.model.commit()
        self.msgbox("已寫出契約檔",
                    f"02_sheets.csv 與 02_sheet_tiles.csv\n\n"
                    f"圖 {r['sheets']} 張／片 {r['tiles']} 片"
                    + (f"\n跳過：{'、'.join(r['skipped'])}" if r["skipped"] else "")
                    + (f"\n\n⚠ 還有 {r['tray']} 片沒分配，沒有寫進去"
                       if r["tray"] else ""))

    def msgbox(self, title, text):
        d = tk.Toplevel(self.root)
        d.title(title)
        d.configure(bg=W.FACE)
        d.transient(self.root)
        b = W.Bevel(d, kind="raised", width=2, bg=W.FACE)
        b.pack(fill="both", expand=True, padx=3, pady=3)
        tk.Label(b.inner, text=text, bg=W.FACE, justify="left",
                 font=W.ui_font(12)).pack(padx=16, pady=12)
        W.Win95Button(b.inner, text="確定", command=d.destroy, width=80).pack(pady=(0, 10))
        d.update_idletasks()
        d.grab_set()

    # ── 校對 ──────────────────────────────────────────────────────────
    def pane_review(self, p):
        tiles = self.model.reviewable()
        if not tiles:
            info = W.Bevel(p, kind="sunken", width=1, bg="#ffffe1")
            info.pack(fill="x", padx=10, pady=10)
            tk.Label(info.inner, bg="#ffffe1", justify="left", font=W.ui_font(12),
                     text="這個案子還沒有任何片跑過辨識。\n\n"
                          "校對的對象是 02_understanding_<片>.json —— 先辨識才有東西可校。"
                     ).pack(anchor="w", padx=10, pady=8)
            return
        if self.rev_tile not in tiles:
            self.rev_tile = tiles[0]
        self.review_root = p
        self.refresh_review()

    def refresh_review(self):
        p = self.review_root
        for c in p.winfo_children():
            c.destroy()
        rev = self.model.review(self.rev_tile)
        els = rev.merged()
        st = rev.stats()

        bar = tk.Frame(p, bg=W.FACE)
        bar.pack(fill="x", padx=6, pady=(6, 2))
        for t in self.model.reviewable():
            W.Win95Button(bar, text=t, width=56,
                          command=lambda k=t: (setattr(self, "rev_tile", k),
                                               self.refresh_review())).pack(side="left")
        for lab, key in (("原掃描", "orig"), ("重建", "rec")):
            W.Win95Button(bar, text=lab, width=66,
                          command=lambda k=key: (setattr(self, "rev_view", k),
                                                 self.refresh_review())
                          ).pack(side="left", padx=(6, 0))
        tk.Label(bar, bg=W.FACE, fg=W.GRAY, font=W.ui_font(11),
                 text=f"　未處理 {st['pending']}　已確認 {st['confirmed']}　"
                      f"退件 {st['rejected']}　修改 {st['edited']}").pack(side="left")

        body = tk.Frame(p, bg=W.FACE)
        body.pack(fill="both", expand=True, padx=6, pady=(0, 6))

        side = tk.Frame(body, bg=W.FACE, width=300)
        side.pack(side="right", fill="y", padx=(4, 0))
        side.pack_propagate(False)
        lb_box = W.Bevel(side, kind="sunken", width=2, bg=W.FIELD)
        lb_box.pack(fill="both", expand=True)
        lb = tk.Listbox(lb_box.inner, bg=W.FIELD, fg=W.TEXT, font=W.ui_font(11),
                        bd=0, highlightthickness=0, selectbackground=W.NAVY,
                        selectforeground=W.WHITE, activestyle="none")
        lb.pack(side="left", fill="both", expand=True)
        lsb = ttk.Scrollbar(lb_box.inner, orient="vertical", command=lb.yview)
        lsb.pack(side="right", fill="y")
        lb.configure(yscrollcommand=lsb.set)
        mark = {"pending": "・", "confirmed": "✔", "rejected": "✘", "edited": "✎"}
        for e in els:
            lb.insert("end", f" {mark[e['status']]} {R.K.ZH.get(e['type'], e['type'])}"
                             f"  {e['conf']}  {e.get('text', '')[:14]}")
        lb.bind("<<ListboxSelect>>",
                lambda _e: self.pick_el(els, lb.curselection()))

        form = tk.Frame(side, bg=W.FACE)
        form.pack(fill="x", pady=4)
        self.cls_var = tk.StringVar(value=els[0]["type"] if els else "wall")
        cb = ttk.Combobox(form, textvariable=self.cls_var, state="readonly",
                          values=[f"{n}　{z}" for n, z in R.CLASS_LIST], height=16)
        cb.pack(fill="x", pady=1)
        self.note_e = tk.Entry(form, bg=W.FIELD, font=W.ui_font(11))
        self.note_e.pack(fill="x", pady=1)
        row = tk.Frame(form, bg=W.FACE)
        row.pack(fill="x")
        for txt, stv in (("✔ 確認", "confirmed"), ("✘ 退件", "rejected"),
                         ("✎ 存改", "edited"), ("↺", "pending")):
            W.Win95Button(row, text=txt, width=70,
                          command=lambda k=stv: self.act_rule(k)).pack(side="left", padx=1)

        askbox = W.Bevel(side, kind="sunken", width=2, bg=W.FIELD)
        askbox.pack(fill="x", pady=(4, 0))
        self.ask_e = tk.Entry(askbox.inner, bg=W.FIELD, font=W.ui_font(11))
        self.ask_e.pack(fill="x")
        self.ask_e.bind("<Return>", lambda _e: self.act_ask())
        W.Win95Button(side, text="問 AI（約 30–90 秒）", command=self.act_ask,
                      width=290).pack(fill="x", pady=2)
        self.ask_out = tk.Label(side, bg=W.FACE, fg=W.TEXT, font=W.ui_font(11),
                                justify="left", wraplength=290, anchor="nw")
        self.ask_out.pack(fill="both", expand=False)

        cbox = W.Bevel(body, kind="sunken", width=2, bg=W.FIELD)
        cbox.pack(side="left", fill="both", expand=True)
        self.canvas = tk.Canvas(cbox.inner, bg=W.FIELD, bd=0, highlightthickness=0)
        self.canvas.pack(side="left", fill="both", expand=True)
        vsb = ttk.Scrollbar(cbox.inner, orient="vertical", command=self.canvas.yview)
        vsb.pack(side="right", fill="y")
        self.canvas.configure(yscrollcommand=vsb.set, yscrollincrement=30)
        png = rev.reconstruction() if self.rev_view == "rec" else rev.original()
        self.imgs["__base"] = png_photo(png)
        self.canvas.create_image(0, 0, image=self.imgs["__base"], anchor="nw")
        self.draw_boxes(els)
        self.canvas.configure(scrollregion=self.canvas.bbox("all"))
        W.wheel_bind(self.canvas)
        self.canvas.bind("<Button-1>", lambda e: self.canvas_click(e, els))
        self.refresh_status()

    def draw_boxes(self, els):
        """框一律給 fill + stipple —— 空心矩形只有邊線算命中（坑 5）。"""
        self.canvas.delete("box")
        for e in els:
            b = [v * REV_SCALE for v in e["box"]]
            col = BOX_COLOR[e["status"]]
            self.canvas.create_rectangle(
                b[0], b[1], b[2], b[3], outline=col, fill=col,
                stipple="gray12", width=3 if e["id"] == self.sel_el else 1,
                tags=("box", f"eid={e['id']}"))

    def canvas_click(self, e, els):
        x = self.canvas.canvasx(e.x); y = self.canvas.canvasy(e.y)
        hits = [i for i in self.canvas.find_overlapping(x - 2, y - 2, x + 2, y + 2)
                if "box" in self.canvas.gettags(i)]
        if not hits:
            return
        tags = self.canvas.gettags(hits[-1])          # 最上層在最後
        eid = next((t[4:] for t in tags if t.startswith("eid=")), None)
        self.sel_el = eid
        el = next((z for z in els if z["id"] == eid), None)
        if el:
            self.cls_var.set(f"{el['type']}　{R.K.ZH.get(el['type'], '')}")
        self.draw_boxes(els)

    def act_rule(self, status):
        if not self.sel_el:
            return
        rev = self.model.review(self.rev_tile)
        rev.rule(self.sel_el, status, self.cls_var.get().split("　")[0],
                 "", self.note_e.get())
        self.refresh_review()

    def pick_el(self, els, sel):
        if not sel:
            return
        e = els[sel[0]]
        self.sel_el = e["id"]
        self.cls_var.set(f"{e['type']}　{R.K.ZH.get(e['type'], '')}")
        self.draw_boxes(els)
        b = [v * REV_SCALE for v in e["box"]]
        top = self.canvas.bbox("all")
        if top and top[3]:
            self.canvas.yview_moveto(max(0.0, (b[1] - 200) / top[3]))

    def act_ask(self):
        q = self.ask_e.get().strip()
        if not q or self.job.is_running():
            return
        self.ask_out.configure(text="…思考中（曬圖判讀約 30–90 秒）")
        rev = self.model.review(self.rev_tile)
        eid = self.sel_el
        # ⚠ 背景只回傳結果，畫面一律等回到主執行緒才動（見檔頭）
        self.job.start(lambda: rev.ask(q, eid), self.ask_done)

    def ask_done(self, ok, res):
        if not ok:
            self.ask_out.configure(text=f"✘ {type(res).__name__}: {res}")
            return
        self.ask_out.configure(text=res["text"][:1200] +
                               f"\n\n（累計 ${res['cost']}）")

    # ── 成果 ──────────────────────────────────────────────────────────
    def pane_book(self, p):
        self.book_root = p
        self.refresh_book()

    def refresh_book(self):
        p = self.book_root
        for c in p.winfo_children():
            c.destroy()
        sheets = [s for s in self.model.view()["sheets"] if s["cells"]]
        if not sheets:
            tk.Label(p, text="還沒有排好的圖", bg=W.FACE, font=W.ui_font(12)
                     ).pack(padx=10, pady=10)
            return
        self.page = max(0, min(self.page, len(sheets) - 1))
        s = sheets[self.page]

        bar = tk.Frame(p, bg=W.FACE)
        bar.pack(fill="x", padx=6, pady=6)
        W.Win95Button(bar, text="◀ 上一頁", width=90,
                      command=lambda: (setattr(self, "page", self.page - 1),
                                       self.refresh_book())).pack(side="left")
        W.Win95Button(bar, text="下一頁 ▶", width=90,
                      command=lambda: (setattr(self, "page", self.page + 1),
                                       self.refresh_book())).pack(side="right")
        tk.Label(bar, bg=W.FACE, font=W.ui_font(13, True),
                 text=f"{s['sheet_id']}　{s.get('drawing_name') or '（無圖名）'}"
                      + ("　【已跳過】" if s.get("skip") else "")).pack()

        box = W.Bevel(p, kind="sunken", width=2, bg=W.FIELD)
        box.pack(fill="both", expand=True, padx=6)
        png = A.preview(self.model.case, s, scale=0.055)
        if png:
            self.imgs["__book"] = png_photo(png)
            tk.Label(box.inner, image=self.imgs["__book"], bg=W.FIELD, bd=0
                     ).pack(padx=4, pady=4)

        pl = self.model.placement()
        tbl = tk.Frame(p, bg=W.FACE)
        tbl.pack(fill="x", padx=6, pady=6)
        cols = ("片", "格", "標題欄", "dx", "dy", "tier", "px/cm")
        for j, c in enumerate(cols):
            W.Bevel(tbl, kind="raised", width=1, bg=W.FACE).grid(row=0, column=j, sticky="ew")
            tk.Label(tbl, text=c, bg=W.FACE, font=W.ui_font(11, True)
                     ).grid(row=0, column=j, padx=8)
        for i, (k, t) in enumerate(sorted(s["cells"].items()), start=1):
            q = pl.get(t, {})
            info = self.model.view()["info"].get(t, {})
            for j, val in enumerate((t, k, info.get("part", "—") if info.get("has_tb")
                                     else "—", q.get("dx", "—"), q.get("dy", "—"),
                                     q.get("tier", "—"), q.get("px_per_cm") or "—")):
                tk.Label(tbl, text=val, bg=W.FACE, font=W.ui_font(11)
                         ).grid(row=i, column=j, padx=8, sticky="w")
        tk.Label(p, bg=W.FACE, fg=W.GRAY, font=W.ui_font(11),
                 text=f"第 {self.page + 1} / {len(sheets)} 頁　"
                      f"樓層 {s.get('floor_text') or '—'}　"
                      "對接預覽未扣重疊（相鄰 A3 約 26%）").pack(pady=(0, 6))

    # ── 進度 ──────────────────────────────────────────────────────────
    def pane_prog(self, p):
        s = self.model.stats()
        tk.Label(p, text="整體進度", bg=W.FACE, font=W.ui_font(12, True)
                 ).pack(anchor="w", padx=10, pady=(10, 2))
        bar = W.Bevel(p, kind="sunken", width=2, bg=W.FIELD)
        bar.pack(fill="x", padx=10)
        inner = tk.Frame(bar.inner, bg=W.FIELD, height=20)
        inner.pack(fill="x")
        inner.pack_propagate(False)
        for _ in range(round(s["pct"] / 100 * 40)):
            tk.Frame(inner, bg=W.NAVY, width=10, height=16).pack(side="left", padx=1, pady=2)
        tk.Label(p, bg=W.FACE, font=W.ui_font(12),
                 text=f"{s['placed']} 片已排定、{s['deleted']} 片已刪除，"
                      f"共 {s['total']} 片　—— {s['pct']}%"
                 ).pack(anchor="w", padx=10, pady=4)

        tk.Label(p, text="成就（只是回饋，不影響任何判斷）", bg=W.FACE,
                 font=W.ui_font(12, True)).pack(anchor="w", padx=10, pady=(8, 2))
        grid = tk.Frame(p, bg=W.FACE)
        grid.pack(fill="x", padx=10)
        for i, b in enumerate(s["badges"]):
            cell = W.Bevel(grid, kind="sunken", width=1, bg=W.FIELD)
            cell.grid(row=i // 3, column=i % 3, sticky="ew", padx=2, pady=2)
            tk.Label(cell.inner, bg=W.FIELD, justify="left", anchor="w",
                     fg=W.TEXT if b["got"] else W.GRAY, font=W.ui_font(11),
                     text=f"{'🏆' if b['got'] else '　'} {b['name']}\n　 {b['desc']}"
                     ).pack(anchor="w", padx=6, pady=3)

        tk.Label(p, bg=W.FACE, fg=W.GRAY, font=W.ui_font(11), justify="left",
                 text=f"\n度量層：有實測錨點的片 {s['tier_good']} / {s['placed']}\n"
                      f"校對：人工確認的框 {s['reviewed']} 個"
                      "（累積到門檻才輪得到 YOLO）\n\n"
                      f"在終端機執行：python3 -m perception.s01c_register "
                      f"cases/{self.model.name}").pack(anchor="w", padx=10, pady=6)


# ─────────────────────────────────────────────────────────────────────────
def selftest():
    """檢查這一份建置是不是真的能跑。

    ⚠ **沒有案件資料不等於建置壞掉。** 環境檢查（Tk、影像、Canvas、模組）
    一律跑；跟案件資料有關的那幾項在沒有 `cases/` 時標成「略過」而不是失敗 ——
    CI 上的乾淨 checkout 本來就沒有案件（那些是使用者資料，照 .gitignore 不進版控）。
    這樣 CI 才驗得到「凍結後的執行檔在那個作業系統上真的開得起來」，
    而那正是開發機（Intel Mac）唯一驗不到 Windows 的補救辦法。
    """
    ok = fail = skip = 0

    def chk(name, cond, extra=""):
        nonlocal ok, fail
        if cond:
            ok += 1
            print(f"  OK   {name}" + (f"  [{extra}]" if extra else ""))
        else:
            fail += 1
            print(f"  FAIL {name}" + (f"  [{extra}]" if extra else ""))

    def skipped(name, why):
        nonlocal skip
        skip += 1
        print(f"  --   {name}　（略過：{why}）")

    print(f"\n{APP_NAME if (APP_NAME := 'Paper-to-BIM') else ''} 自我檢查")
    print(f"  凍結：{bool(getattr(sys, 'frozen', False))}　"
          f"案件目錄：{CASES}")

    # ── 環境：這一組跟使用者資料無關，任何情況都要過 ──
    root = tk.Tk(); root.withdraw()
    try:
        W.install_clam(root)
        chk("tkinter 起得來", True, root.tk.call("info", "patchlevel"))
        chk("cv2 / numpy 載得起來", bool(cv2.__version__),
            f"cv2 {cv2.__version__}")
        png = cv2.imencode(".png", np.full((12, 20, 3), 200, np.uint8))[1].tobytes()
        img = png_photo(png)
        chk("PNG 進得了 PhotoImage", (img.width(), img.height()) == (20, 12))
        c = tk.Canvas(root)
        c.create_rectangle(0, 0, 9, 9, fill="#c05028", stipple="gray12",
                           tags=("box", "eid=x"))
        chk("stipple 半透明框畫得出來", "box" in c.gettags(c.find_all()[0]))
        chk("find_overlapping 找得到", c.find_overlapping(1, 1, 2, 2) != ())
        b = W.Bevel(root, kind="raised", width=2)
        chk("Win95 立體邊框建得起來", b.inner is not None)
        chk("契約類別引得到", len(R.CLASS_LIST) >= 15, f"{len(R.CLASS_LIST)} 類")

        # ── 資料：有案子才驗 ──
        cases = case_list()
        if not cases:
            for n in ("排圖提案", "統計", "縮圖", "對接預覽", "校對"):
                skipped(n, f"{CASES} 底下沒有案件")
        else:
            m = Model(cases[0])
            v = m.view()
            chk("排圖提案載入", len(v["sheets"]) > 0, f"{len(v['sheets'])} 張")
            st = m.stats()
            chk("統計算得出來", st["total"] > 0,
                f"{st['placed']}/{st['total']}　{st['pct']}%")
            chk("成就有九項", len(st["badges"]) == 9)
            t = (v["tray"] or list(v["sheets"][0]["cells"].values()))[0]
            g = cv2.imread(str(m.case / "01_tiles_upright" / f"{t}.png"), 0)
            png = cv2.imencode(".png", cv2.resize(g, (150, 106)))[1].tobytes()
            chk("縮圖進得了 PhotoImage", png_photo(png).width() == 150)
            sh = next(x for x in v["sheets"] if x["cells"])
            chk("對接預覽畫得出來", len(A.preview(m.case, sh, scale=0.05)) > 1000)
            rt = m.reviewable()
            if not rt:
                skipped("校對", "還沒有片跑過辨識")
            else:
                rev = m.review(rt[0])
                chk("校對元素載入", len(rev.merged()) > 0, f"{len(rev.merged())} 個")
                chk("重建圖畫得出來", len(rev.reconstruction()) > 1000)
                chk("訓練資料硬閘只放行人看過的",
                    all(e["status"] in ("confirmed", "edited") for e in rev.labels()),
                    f"{len(rev.labels())} 個")
    finally:
        root.destroy()

    print(f"\n{ok}/{ok + fail} 通過" + (f"，{skip} 項略過" if skip else ""))
    if LOG_PATH:
        print(f"（沒有主控台，輸出同時寫到 {LOG_PATH}）")
    print("⚠ 以下要開視窗才驗得到：拖曳命中、捲動手感、實際像素配色")
    return 0 if fail == 0 else 1


if __name__ == "__main__":
    if "--selftest" in sys.argv:
        sys.exit(selftest())
    try:
        Desktop().run()
    except Exception:                                 # noqa: BLE001
        traceback.print_exc()
        sys.exit(1)
