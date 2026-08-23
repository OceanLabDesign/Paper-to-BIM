"""tools/win95.py —— Windows 95 外觀的 tkinter 控件工具箱（純標準函式庫）

給 `tools/desktop.py` 用。**不開視窗、不碰資料**，只是一組控件。

## 為什麼要自己做這些控件

macOS 的 tk 有六個控件走 Aqua 原生繪製，**設了顏色也畫不出來**（2026-08-23
用 CoreGraphics 讀回真實像素驗證，不是靠 cget()）：

    tk.Button、tk.Scrollbar、tk.Menu、
    tk.Checkbutton/tk.Radiobutton 的指示器、tk.Spinbox 的箭頭、tk.OptionMenu

實測 `tk.Button(bg="#ff0000")` 中心像素是 (240,240,240) —— 鮮紅一個像素都沒有；
同樣設定的 `tk.Label` 是 (192,192,192)，逐字命中。
**可以塗色的是** tk.Frame / Label / Entry / Listbox / Canvas / Text。

## 立體邊框為什麼不用 relief=RAISED

Tk 每一側只畫**一種**顏色，而且暗側是它自己從 bg 算出來的 `#737373`，
不是 Win95 的 `#808080`。實測 `tk.Frame(bg="#c0c0c0", relief=RAISED, bd=2)`
左緣讀回 [(255,255,255),(255,255,255),(192,...)]、右緣 [(116,116,115),(115,114,115),...]
—— 兩層同色，而且 115 ≠ 128。

所以 `Bevel` 用 **4 條 1px tk.Frame 疊兩圈**自己畫。實測左緣
[(255,254,255),(224,223,223),(192,...)]、右緣 [(0,1,0),(127,128,128),...]，
`#ffffff→#dfdfdf` / `#000000→#808080` 完全命中。

## 互動控件走 ttk + clam

`install_clam()` 之後 ttk 才吃得到自訂顏色（aqua 主題下 ttk.Notebook 的
`element_options('Notebook.tab')` 回傳**空 tuple**，零個可設選項）。
捲軸、核取方塊、進度條、分隔線一律用 ttk 版。

## 背景工作：絕對不要從別的執行緒動控件

實測最陰險的一條：**背景執行緒呼叫 widget.config() 在 mainloop 有跑的時候
不會丟例外**，它被偷偷排到主執行緒去。主執行緒忙 2.0 秒時，背景那支
`config()` 卡住 1.690 秒才返回。「我測了沒當掉」不構成安全證據。
`Job` 的作法是：背景只 `queue.put()`，主執行緒 `after()` 輪詢。

來源：2026-08-23 的 macOS/tkinter 實測（Darwin 23.6、Python 3.12.7、Tk 8.6.14、aqua）。
"""

import queue
import subprocess
import sys
import threading
import tkinter as tk
from tkinter import ttk, font as tkfont

FACE   = "#c0c0c0"   # 面板 / 按鈕臉
WHITE  = "#ffffff"   # 最亮
LIGHT  = "#dfdfdf"   # 次亮
SHADOW = "#808080"   # 次暗
BLACK  = "#0a0a0a"   # 最暗（Win95 用 #0a0a0a 不是純黑）
NAVY   = "#000080"   # 標題列 / 選取
TEXT   = "#000000"
GRAY   = "#808080"   # 停用文字
FIELD  = "#ffffff"   # 輸入框底

# 兩明兩暗：外圈 (左上, 右下)、內圈 (左上, 右下)
RINGS = {
    "raised":  [(WHITE,  BLACK), (LIGHT,  SHADOW)],
    "sunken":  [(SHADOW, WHITE), (BLACK,  LIGHT)],
    "pressed": [(BLACK,  WHITE), (SHADOW, LIGHT)],
    "flat":    [(FACE,   FACE),  (FACE,   FACE)],
}

def ui_font(size=12, bold=False):
    """macOS 沒有 MS Sans Serif；Tahoma 是最接近的，中文自動 fallback 到 PingFang TC。"""
    fams = set(tkfont.families())
    for name in ("Tahoma", "MS Sans Serif", "Microsoft Sans Serif", "Geneva", "Helvetica"):
        if name in fams:
            return (name, size, "bold") if bold else (name, size)
    return ("TkDefaultFont", size, "bold") if bold else ("TkDefaultFont", size)

class Bevel(tk.Frame):
    """兩明兩暗立體邊框。內容放進 .inner。切換凹凸用 set_kind()，不要 destroy 重建。

    邊線用 place() 疊 1px 的 Frame；內容區用 grid + weight，這樣子控件的需求尺寸
    才會往上傳（用 place 排內容區會讓容器縮成 1x1）。
    """

    def __init__(self, parent, kind="raised", width=2, bg=FACE, **kw):
        super().__init__(parent, bg=bg, bd=0, highlightthickness=0, **kw)
        self._edges = []
        for k in range(width):
            tl = (tk.Frame(self, bd=0, highlightthickness=0),
                  tk.Frame(self, bd=0, highlightthickness=0))
            br = (tk.Frame(self, bd=0, highlightthickness=0),
                  tk.Frame(self, bd=0, highlightthickness=0))
            tl[0].place(x=k, y=k, relwidth=1, width=-2 * k, height=1)          # 上
            tl[1].place(x=k, y=k, relheight=1, height=-2 * k, width=1)         # 左
            br[0].place(x=k, rely=1, y=-k - 1, relwidth=1, width=-2 * k, height=1)   # 下
            br[1].place(relx=1, x=-k - 1, y=k, relheight=1, height=-2 * k, width=1)  # 右
            self._edges.append((tl, br))
        self.inner = tk.Frame(self, bg=bg, bd=0, highlightthickness=0)
        self.inner.grid(row=0, column=0, sticky="nsew", padx=width, pady=width)
        self.grid_rowconfigure(0, weight=1)
        self.grid_columnconfigure(0, weight=1)
        self.kind = None
        self.set_kind(kind)

    def set_kind(self, kind):
        self.kind = kind
        rings = RINGS[kind]
        for (tl, br), (c1, c2) in zip(self._edges, rings):
            for w in tl:
                w.configure(bg=c1)
            for w in br:
                w.configure(bg=c2)

    def fix_size(self, w=None, h=None):
        """固定尺寸時務必兩種 propagate 都關掉（內容用 grid，容器可能被 pack 管）。"""
        if w or h:
            self.configure(width=w or self.winfo_reqwidth(), height=h or self.winfo_reqheight())
        self.grid_propagate(False)
        self.pack_propagate(False)
        return self

class Win95Button(Bevel):
    def __init__(self, parent, text="", command=None, width=None, height=None, **kw):
        super().__init__(parent, kind="raised", width=2, bg=FACE, **kw)
        self.command, self._enabled, self._down = command, True, False
        self._lab = tk.Label(self.inner, text=text, bg=FACE, fg=TEXT, font=ui_font(),
                             bd=0, highlightthickness=0)
        self._lab.pack(fill="both", expand=True, padx=4, pady=1)
        if width or height:
            self.fix_size(width, height)
        for w in (self, self.inner, self._lab):
            w.bind("<ButtonPress-1>", self._press)
            w.bind("<ButtonRelease-1>", self._release)

    def _press(self, _e=None):
        if not self._enabled:
            return
        self._down = True
        self.set_kind("pressed")
        self._lab.pack_configure(padx=(6, 2), pady=(2, 0))

    def _release(self, e=None):
        if not self._enabled or not self._down:
            return
        self._down = False
        self.set_kind("raised")
        self._lab.pack_configure(padx=4, pady=1)
        inside = (e is None or (0 <= e.x_root - self.winfo_rootx() < self.winfo_width()
                                and 0 <= e.y_root - self.winfo_rooty() < self.winfo_height()))
        if inside and self.command:
            self.command()

    def set_enabled(self, on):
        self._enabled = bool(on)
        self._lab.configure(fg=TEXT if on else GRAY)

    def configure_text(self, text):
        self._lab.configure(text=text)

class Win95Tabs(tk.Frame):
    """自製分頁：當頁 22px 高、y=0；非當頁 18px 高、y=2，當頁下緣壓過面板頂 2px。"""

    STRIP_H, TAB_H, OFF = 22, 22, 4

    def __init__(self, parent, titles, **kw):
        super().__init__(parent, bg=FACE, bd=0, highlightthickness=0, **kw)
        self.strip = tk.Frame(self, bg=FACE, bd=0, highlightthickness=0)
        self.strip.place(x=0, y=0, relwidth=1, height=self.STRIP_H)
        self.panel = Bevel(self, kind="raised", width=2, bg=FACE)
        self.panel.place(x=0, y=self.STRIP_H - 2, relwidth=1, relheight=1,
                         height=-(self.STRIP_H - 2))
        self.pages, self._tabs, self._geo, self.current = [], [], [], 0
        f = tkfont.Font(font=ui_font())
        x = 2
        for i, t in enumerate(titles):
            w = f.measure(t) + 22
            tab = self._make_tab(t)
            self._tabs.append(tab)
            self._geo.append((x, w))
            x += w - 2
            page = tk.Frame(self.panel.inner, bg=FACE, bd=0, highlightthickness=0)
            self.pages.append(page)
            for wid in (tab,) + tuple(tab.winfo_children()):
                wid.bind("<Button-1>", lambda _e, k=i: self.select(k))
        self.select(0)

    def _make_tab(self, text):
        """Win95 分頁：左/上亮、右暗，下緣不畫（要跟面板連成一體）。"""
        t = tk.Frame(self.strip, bg=FACE, bd=0, highlightthickness=0)
        tk.Frame(t, bg=WHITE, bd=0, highlightthickness=0).place(x=1, y=0, relwidth=1, width=-3, height=1)
        tk.Frame(t, bg=WHITE, bd=0, highlightthickness=0).place(x=0, y=1, relheight=1, height=-1, width=1)
        tk.Frame(t, bg=SHADOW, bd=0, highlightthickness=0).place(relx=1, x=-2, y=1, relheight=1, height=-1, width=1)
        tk.Frame(t, bg=BLACK, bd=0, highlightthickness=0).place(relx=1, x=-1, y=2, relheight=1, height=-2, width=1)
        lab = tk.Label(t, text=text, bg=FACE, fg=TEXT, font=ui_font(), bd=0, highlightthickness=0)
        lab.place(x=2, y=1, relwidth=1, width=-5, relheight=1, height=-2)
        return t

    def select(self, idx):
        self.current = idx
        for i, tab in enumerate(self._tabs):
            x, w = self._geo[i]
            on = (i == idx)
            tab.place(x=x if on else x + 2, y=0 if on else 2,
                      width=w if on else w - 4, height=self.TAB_H if on else self.TAB_H - 4)
            tab.lift() if on else tab.lower()
        for i, p in enumerate(self.pages):
            p.place(x=0, y=0, relwidth=1, relheight=1) if i == idx else p.place_forget()
        self._tabs[idx].lift()

class Win95MenuBar(tk.Frame):
    def __init__(self, parent, spec, **kw):
        """spec = [("檔案(F)", [("開啟…", fn), ("-", None), ("結束", fn)]), ...]"""
        super().__init__(parent, bg=FACE, bd=0, highlightthickness=0, **kw)
        self.spec, self._pop, self._open_idx = spec, None, None
        f = tkfont.Font(font=ui_font())
        x = 2
        self._labs = []
        for i, (title, items) in enumerate(spec):
            w = f.measure(title) + 16
            lab = tk.Label(self, text=title, bg=FACE, fg=TEXT, font=ui_font(),
                           bd=0, highlightthickness=0)
            lab.place(x=x, y=1, width=w, height=18)
            lab.bind("<Button-1>", lambda _e, k=i: self.open(k))
            lab.bind("<Enter>", lambda e: e.widget.configure(bg=NAVY, fg=WHITE))
            lab.bind("<Leave>", lambda e, k=i: None if self._open_idx == k
                     else e.widget.configure(bg=FACE, fg=TEXT))
            self._labs.append(lab)
            x += w

    def close(self, _e=None):
        if self._pop is not None:
            try:
                self._pop.grab_release()
                self._pop.destroy()
            except tk.TclError:
                pass
            self._pop = None
        if self._open_idx is not None:
            try:
                self._labs[self._open_idx].configure(bg=FACE, fg=TEXT)
            except tk.TclError:
                pass
            self._open_idx = None

    def open(self, idx):
        if self._open_idx == idx:
            self.close()
            return
        self.close()
        self._open_idx = idx
        lab = self._labs[idx]
        lab.configure(bg=NAVY, fg=WHITE)
        items = self.spec[idx][1]
        pop = tk.Toplevel(self)
        pop.overrideredirect(True)
        pop.configure(bg=FACE)
        try:
            pop.attributes("-topmost", True)
        except tk.TclError:
            pass
        box = Bevel(pop, kind="raised", width=2, bg=FACE)
        box.pack(fill="both", expand=True)
        f = tkfont.Font(font=ui_font())
        wdt = max(f.measure(t) for t, _ in items) + 44
        for text, fn in items:
            if text == "-":
                sep = tk.Frame(box.inner, bg=FACE, height=7, bd=0, highlightthickness=0)
                sep.pack(fill="x")
                tk.Frame(sep, bg=SHADOW, height=1, bd=0).place(x=2, y=3, relwidth=1, width=-4)
                tk.Frame(sep, bg=WHITE, height=1, bd=0).place(x=2, y=4, relwidth=1, width=-4)
                continue
            row = tk.Label(box.inner, text=text, bg=FACE, fg=TEXT, font=ui_font(),
                           anchor="w", bd=0, highlightthickness=0, width=1)
            row.pack(fill="x", ipady=2)
            row.bind("<Enter>", lambda e: e.widget.configure(bg=NAVY, fg=WHITE))
            row.bind("<Leave>", lambda e: e.widget.configure(bg=FACE, fg=TEXT))
            row.bind("<Button-1>", lambda _e, g=fn: (self.close(), g and g()))
        pop.update_idletasks()
        pop.geometry("%dx%d+%d+%d" % (wdt, box.winfo_reqheight(),
                                      lab.winfo_rootx(), lab.winfo_rooty() + 18))
        # overrideredirect 的 Toplevel 在 macOS 拿不到鍵盤焦點，<FocusOut> 永遠不觸發；
        # 只能靠 grab + 在選單本體綁 <Button-1>（有 grab 時點外面的事件也會送進來）。
        pop.bind("<Button-1>", self.close)
        try:
            pop.grab_set()
        except tk.TclError:
            pass
        self._pop = pop

class Win95StatusBar(tk.Frame):
    def __init__(self, parent, widths=(0, 120, 120), **kw):
        super().__init__(parent, bg=FACE, bd=0, highlightthickness=0, height=22, **kw)
        self.pack_propagate(False)
        self.grid_propagate(False)
        self.panes = []
        for i, w in enumerate(widths):
            b = Bevel(self, kind="sunken", width=1, bg=FACE)
            lab = tk.Label(b.inner, text="", bg=FACE, fg=TEXT, font=ui_font(),
                           anchor="w", bd=0, highlightthickness=0)
            lab.pack(fill="both", expand=True, padx=2)
            self.grid_columnconfigure(i, weight=1 if w == 0 else 0, minsize=w)
            b.grid(row=0, column=i, sticky="nsew", padx=(0, 2))
            self.panes.append(lab)
        self.grid_rowconfigure(0, weight=1)

    def set(self, idx, text):
        self.panes[idx].configure(text=text)

class Job:
    """背景執行緒直接動控件在 mainloop 有跑時「不會丟例外」，但會被序列化到主執行緒
    而卡住（實測卡 1.69 秒）。所以一律 queue + after() 輪詢。"""

    def __init__(self, root, on_event, poll_ms=80):
        self.root, self.on_event, self.poll_ms = root, on_event, poll_ms
        self.q, self.proc, self.thread = queue.Queue(), None, None
        self._stop, self._pump_id = threading.Event(), None

    def _run(self, argv):
        try:
            self.proc = subprocess.Popen(argv, stdout=subprocess.PIPE,
                                         stderr=subprocess.STDOUT, text=True, bufsize=1)
            for line in self.proc.stdout:
                if self._stop.is_set():
                    break
                self.q.put(("line", line.rstrip("\n")))
            self.proc.stdout.close()
            self.q.put(("done", self.proc.wait()))
        except Exception as exc:                      # noqa: BLE001
            self.q.put(("error", repr(exc)))

    def start(self, argv):
        if self.is_running():
            return False
        self._stop.clear()
        self.thread = threading.Thread(target=self._run, args=(argv,), daemon=True)
        self.thread.start()
        self._pump_id = self.root.after(self.poll_ms, self._pump)
        return True

    def is_running(self):
        return self.thread is not None and self.thread.is_alive()

    def _pump(self):
        try:
            while True:
                self.on_event(*self.q.get_nowait())
        except queue.Empty:
            pass
        self._pump_id = (self.root.after(self.poll_ms, self._pump)
                         if self.is_running() or not self.q.empty() else None)

    def shutdown(self, timeout=2.0):
        if self._pump_id:
            try:
                self.root.after_cancel(self._pump_id)
            except tk.TclError:
                pass
            self._pump_id = None
        self._stop.set()
        if self.proc and self.proc.poll() is None:
            self.proc.terminate()
            try:
                self.proc.wait(timeout=timeout)
            except subprocess.TimeoutExpired:
                self.proc.kill()
        if self.thread:
            self.thread.join(timeout=timeout)

def install_clam(root):
    st = ttk.Style(root)
    st.theme_use("clam")
    st.configure(".", background=FACE, foreground=TEXT, fieldbackground=FIELD,
                 troughcolor=FACE, bordercolor=BLACK, lightcolor=WHITE, darkcolor=SHADOW,
                 focuscolor=FACE, selectbackground=NAVY, selectforeground=WHITE,
                 arrowcolor=TEXT, insertcolor=TEXT, borderwidth=2, relief="raised",
                 font=ui_font())
    # 捲軸：內容塞得下時 ttk 會把它切成 disabled，clam 的 disabled 會拉回自己的
    # 米灰 #dcdad5（實測洩漏 2755 px）。configure 蓋不掉狀態相依的值，一定要用 map。
    for cls in ("TScrollbar", "Vertical.TScrollbar", "Horizontal.TScrollbar"):
        st.configure(cls, troughcolor=FACE, background=FACE, bordercolor=BLACK,
                     lightcolor=WHITE, darkcolor=SHADOW, arrowcolor=TEXT, borderwidth=2)
        st.map(cls,
               background=[("disabled", FACE), ("active", FACE), ("pressed", FACE),
                           ("!disabled", FACE)],
               troughcolor=[("disabled", FACE), ("!disabled", FACE)],
               bordercolor=[("disabled", BLACK), ("!disabled", BLACK)],
               lightcolor=[("disabled", WHITE), ("!disabled", WHITE)],
               darkcolor=[("disabled", SHADOW), ("!disabled", SHADOW)],
               arrowcolor=[("disabled", SHADOW), ("!disabled", TEXT)])
    for cls in ("TCheckbutton", "TRadiobutton"):
        st.configure(cls, indicatorbackground=FIELD, indicatorforeground=TEXT,
                     upperbordercolor=SHADOW, lowerbordercolor=WHITE, focuscolor=FACE)
    st.configure("TSeparator", background=SHADOW)          # 只吃 background
    st.configure("Horizontal.TProgressbar", background=NAVY, troughcolor=FACE,
                 bordercolor=BLACK, lightcolor=NAVY, darkcolor=NAVY)
    st.map("TButton", relief=[("pressed", "sunken")],
           lightcolor=[("pressed", SHADOW)], darkcolor=[("pressed", WHITE)])
    return st

def wheel_bind(widget, target=None):
    """Canvas/Listbox 在 aqua 沒有內建滾輪綁定；delta 是「格數」(±1) 不是 Windows 的 ±120。"""
    target = target or widget

    def on_wheel(e):
        n = -e.delta if abs(e.delta) < 30 else -e.delta // 120
        target.yview_scroll(n or (-1 if e.delta > 0 else 1), "units")
    widget.bind("<MouseWheel>", on_wheel)


class ThreadJob:
    """把任何 Python 呼叫丟到背景執行緒，結果經 queue 回主執行緒。

    跟 Job 的差別只在跑的是 callable 不是子行程；**不動控件**這條鐵則一樣 ——
    背景只 put，主執行緒 after() 輪詢之後才碰畫面。
    """

    def __init__(self, root, poll_ms=80):
        self.root, self.poll_ms = root, poll_ms
        self.q, self.thread, self._pump_id = queue.Queue(), None, None

    def is_running(self):
        return self.thread is not None and self.thread.is_alive()

    def start(self, fn, on_done, *a, **kw):
        """on_done(ok: bool, result_or_exception) 會在主執行緒被呼叫。"""
        if self.is_running():
            return False

        def run():
            try:
                self.q.put((True, fn(*a, **kw)))
            except Exception as exc:                  # noqa: BLE001
                self.q.put((False, exc))

        self.thread = threading.Thread(target=run, daemon=True)
        self.thread.start()
        self._pump_id = self.root.after(self.poll_ms, self._pump, on_done)
        return True

    def _pump(self, on_done):
        try:
            ok, res = self.q.get_nowait()
        except queue.Empty:
            self._pump_id = (self.root.after(self.poll_ms, self._pump, on_done)
                             if self.is_running() else None)
            return
        self._pump_id = None
        on_done(ok, res)

    def shutdown(self):
        if self._pump_id:
            try:
                self.root.after_cancel(self._pump_id)
            except tk.TclError:
                pass
            self._pump_id = None
