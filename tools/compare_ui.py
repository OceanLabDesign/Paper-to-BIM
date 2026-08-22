"""tools/compare_ui.py —— 即時對照檢視器

`python3 tools/compare_ui.py [案件資料夾]` → 開 http://127.0.0.1:8710

左右滑桿拖動比較「原掃描」與「理解後重繪」，右側可即時調參數重跑。
只用標準函式庫的 http.server，不加任何相依。

為什麼要這個：loop engineering 的閉環需要**看得到改動的效果**。
先前每次調參數都要跑腳本、存圖、開圖，一輪要一分鐘；這裡是即時的。
"""

import base64
import io
import json
import math
import sys
import urllib.parse
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.dont_write_bytecode = True

import cv2                                                     # noqa: E402
import numpy as np                                             # noqa: E402
from core.config import PX_PER_CM                              # noqa: E402

CASE = Path(sys.argv[1]) if len(sys.argv) > 1 else ROOT / "cases" / "79-B37001_七賢二路"
PORT = 8710
_cache = {}


def load_tile(tid):
    if tid not in _cache:
        p = CASE / "01_tiles_upright" / f"{tid}.png"
        _cache[tid] = cv2.imread(str(p), 0)
    return _cache[tid]


def binarize(gray, block, c, min_area, crease):
    b = (cv2.adaptiveThreshold(gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
                               cv2.THRESH_BINARY_INV, block | 1, c) > 0).astype(np.uint8)
    if min_area > 1:
        n, lab, st, _ = cv2.connectedComponentsWithStats(b, 8)
        keep = np.zeros(n, np.uint8)
        keep[[i for i in range(1, n) if st[i][4] >= min_area]] = 1
        b = keep[lab]
    h, w = b.shape
    b[int(h * 0.80):, :] = 0                                   # 標題欄帶
    if crease:
        b[:, crease[0]:crease[1]] = 0                          # 摺痕帶
    return b


def _form(s):
    x1, y1, x2, y2 = map(float, s)
    a = math.atan2(y2 - y1, x2 - x1) % math.pi
    return math.degrees(a), -math.sin(a) * x1 + math.cos(a) * y1


def understand(b, p):
    """理解：把線分成「等距梳狀＝樓梯」與「相鄰線對＝牆」，而不是逐條描。"""
    ls = cv2.HoughLinesP(b * 255, 1, np.pi / 180, p["hough"],
                         minLineLength=p["minlen"], maxLineGap=p["maxgap"])
    if ls is None:
        return [], [], 0
    ls = ls[:, 0]
    fam = {45: [], 135: []}
    for s in ls:
        a, o = _form(s)
        for k in (45, 135):
            if abs(a - k) < p["angtol"]:
                fam[k].append((o, math.dist((s[0], s[1]), (s[2], s[3])), s))

    walls, stairs = [], []
    for k, items in fam.items():
        items.sort()
        cl = []
        for o, L, s in items:
            if cl and o - cl[-1]["hi"] < 10:
                cl[-1].update(hi=o); cl[-1]["w"] += L
                cl[-1]["os"].append(o); cl[-1]["seg"].append(s)
            else:
                cl.append({"hi": o, "w": L, "os": [o], "seg": [s]})
        cl = [c for c in cl if c["w"] > p["minink"]]
        for c in cl:
            c["o"] = float(np.mean(c["os"])); c["ang"] = k
        if not cl:
            continue

        def ext(c):
            P = np.array([q for s in c["seg"] for q in ((s[0], s[1]), (s[2], s[3]))], float)
            u = np.array([math.cos(math.radians(k)), math.sin(math.radians(k))])
            t = P @ u
            return P[t.argmin()], P[t.argmax()]

        used, i = set(), 0
        while i < len(cl) - 2:                                  # 梳狀 → 樓梯
            run, j, gm = [i], i, None
            while j + 1 < len(cl):
                d = cl[j + 1]["o"] - cl[j]["o"]
                if 20 <= d <= 45 and (gm is None or abs(d - gm) < 8):
                    run.append(j + 1); j += 1
                    gm = float(np.mean([cl[r]["o"] - cl[r - 1]["o"] for r in run[1:]]))
                else:
                    break
            if len(run) >= p["minsteps"]:
                p0, _ = ext(cl[run[0]]); _, p1 = ext(cl[run[-1]])
                stairs.append({"ang": k, "n": len(run), "tread_cm": round(gm / PX_PER_CM, 1),
                               "o0": cl[run[0]]["o"], "o1": cl[run[-1]]["o"],
                               "p0": p0.tolist(), "p1": p1.tolist()})
                used |= set(run); i = run[-1] + 1
            else:
                i += 1
        rest = [c for idx, c in enumerate(cl) if idx not in used]
        for a_, b_ in zip(rest, rest[1:]):                      # 線對 → 牆
            d = b_["o"] - a_["o"]
            if p["wall_lo"] <= d <= p["wall_hi"]:
                q0, q1 = ext(a_)
                walls.append({"ang": k, "off": (a_["o"] + b_["o"]) / 2,
                              "th_cm": round(d / PX_PER_CM, 1),
                              "p0": q0.tolist(), "p1": q1.tolist(),
                              "len_m": round(math.dist(q0, q1) / PX_PER_CM / 100, 2)})
    keep = []
    for w in sorted(walls, key=lambda r: -r["len_m"]):
        if not any(abs(x["ang"] - w["ang"]) < 3 and abs(x["off"] - w["off"]) < 45 for x in keep):
            keep.append(w)
    return keep, stairs, len(ls)


def render(shape, walls, stairs):
    h, w = shape
    img = np.full((h, w, 3), 255, np.uint8)
    for x in walls:
        t = max(3, int(x["th_cm"] * PX_PER_CM))
        a, b = tuple(map(int, x["p0"])), tuple(map(int, x["p1"]))
        cv2.line(img, a, b, (30, 30, 30), t)
        cv2.line(img, a, b, (255, 255, 255), max(1, t - 6))
    for s in stairs:
        ang = math.radians(s["ang"]); u = np.array([math.cos(ang), math.sin(ang)])
        nv = np.array([-u[1], u[0]]); p0 = np.array(s["p0"])
        L = math.dist(s["p0"], s["p1"]); span = abs(s["o1"] - s["o0"])
        for i in range(s["n"]):
            base = p0 + nv * (i * span / max(1, s["n"] - 1))
            cv2.line(img, tuple(base.astype(int)), tuple((base + u * L).astype(int)), (90, 90, 90), 2)
        for off in (0, span):
            q = p0 + nv * off
            cv2.line(img, tuple(q.astype(int)), tuple((q + u * L).astype(int)), (0, 0, 200), 3)
    return img


def png_b64(img, scale=0.22):
    small = cv2.resize(img, (0, 0), fx=scale, fy=scale, interpolation=cv2.INTER_AREA)
    ok, buf = cv2.imencode(".png", small)
    return base64.b64encode(buf).decode()


HTML = """<!doctype html><meta charset=utf-8><title>Paper-to-BIM 對照</title>
<style>
 body{margin:0;font:13px/1.5 -apple-system,"Noto Sans TC",sans-serif;background:#111;color:#ddd;display:flex}
 #left{flex:1;position:relative;overflow:hidden;background:#000}
 #wrap{position:relative;width:100%;height:100vh;display:flex;align-items:center;justify-content:center}
 #a,#b{position:absolute;max-width:100%;max-height:100vh;user-select:none}
 #b{clip-path:inset(0 0 0 50%)}
 #bar{position:absolute;top:0;bottom:0;left:50%;width:2px;background:#0af;cursor:ew-resize;z-index:5}
 #bar::after{content:"◀▶";position:absolute;top:50%;left:-19px;background:#0af;color:#000;padding:2px 4px;border-radius:3px;font-size:11px}
 .tag{position:absolute;top:8px;padding:3px 8px;background:#0009;border-radius:3px;z-index:4}
 #panel{width:280px;padding:14px;background:#1a1a1a;overflow-y:auto;height:100vh;box-sizing:border-box}
 h3{margin:0 0 10px;font-size:14px;color:#0af}
 label{display:block;margin:9px 0 2px;color:#999;font-size:11px}
 input[type=range]{width:100%}
 .v{float:right;color:#0af}
 button{width:100%;padding:8px;margin-top:12px;background:#0af;border:0;color:#000;font-weight:600;border-radius:4px;cursor:pointer}
 #stats{margin-top:14px;padding:10px;background:#000;border-radius:4px;font-size:12px;white-space:pre-wrap}
 select{width:100%;background:#000;color:#ddd;border:1px solid #444;padding:4px}
</style>
<div id=left><div id=wrap>
  <img id=a><img id=b><div id=bar></div>
  <span class=tag style="left:8px">原掃描</span><span class=tag style="right:8px">理解後重繪</span>
</div></div>
<div id=panel>
  <h3>Paper-to-BIM 對照</h3>
  <label>圖片 <select id=tile></select></label>
  <div id=ctl></div>
  <button onclick=run()>重新抽取</button>
  <div id=stats>載入中…</div>
</div>
<script>
const P=[["block","二值化區塊",11,61,31,2],["c","二值化 C",2,25,12,1],
 ["min_area","去雜點面積",1,60,12,1],["hough","Hough 門檻",40,200,80,5],
 ["minlen","最短線段",80,500,250,10],["maxgap","允許斷點",2,60,30,2],
 ["angtol","角度容差",1,10,4,1],["minink","線群最少墨水",100,3000,700,50],
 ["wall_lo","牆厚下限 px",6,30,12,1],["wall_hi","牆厚上限 px",20,80,42,1],
 ["minsteps","樓梯最少階數",3,12,5,1]];
const ctl=document.getElementById('ctl');
P.forEach(([k,n,mn,mx,d,st])=>{ctl.insertAdjacentHTML('beforeend',
 `<label>${n}<span class=v id=v_${k}>${d}</span></label>
  <input type=range id=${k} min=${mn} max=${mx} value=${d} step=${st}
   oninput="v_${k}.textContent=this.value">`)});
fetch('/tiles').then(r=>r.json()).then(t=>{
  tile.innerHTML=t.map(x=>`<option>${x}</option>`).join('');
  tile.value=t.includes('p20')?'p20':t[0]; run();});
tile.onchange=run;
function run(){
  const q=new URLSearchParams({tile:tile.value});
  P.forEach(([k])=>q.set(k,document.getElementById(k).value));
  stats.textContent='處理中…';
  fetch('/extract?'+q).then(r=>r.json()).then(d=>{
    a.src='data:image/png;base64,'+d.orig; b.src='data:image/png;base64,'+d.rec;
    stats.textContent=d.stats;});
}
let drag=false;
bar.onmousedown=e=>{drag=true;e.preventDefault()};
onmouseup=()=>drag=false;
onmousemove=e=>{if(!drag)return;
  const r=wrap.getBoundingClientRect();
  const p=Math.max(0,Math.min(100,(e.clientX-r.left)/r.width*100));
  bar.style.left=p+'%'; b.style.clipPath=`inset(0 0 0 ${p}%)`};
</script>"""


class H(BaseHTTPRequestHandler):
    def log_message(self, *a):
        pass

    def _send(self, body, ctype="application/json"):
        data = body if isinstance(body, bytes) else body.encode()
        self.send_response(200)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def do_GET(self):
        u = urllib.parse.urlparse(self.path)
        q = {k: v[0] for k, v in urllib.parse.parse_qs(u.query).items()}
        if u.path == "/":
            return self._send(HTML, "text/html; charset=utf-8")
        if u.path == "/tiles":
            names = sorted(p.stem for p in (CASE / "01_tiles_upright").glob("*.png"))
            return self._send(json.dumps(names))
        if u.path == "/extract":
            tid = q.get("tile", "p20")
            gray = load_tile(tid)
            if gray is None:
                return self._send(json.dumps({"stats": f"{tid} 讀不到"}))
            gi = lambda k, d: int(float(q.get(k, d)))
            b = binarize(gray, gi("block", 31), gi("c", 12), gi("min_area", 12), (1820, 1920))
            p = {"hough": gi("hough", 80), "minlen": gi("minlen", 250),
                 "maxgap": gi("maxgap", 30), "angtol": gi("angtol", 4),
                 "minink": gi("minink", 700), "wall_lo": gi("wall_lo", 12),
                 "wall_hi": gi("wall_hi", 42), "minsteps": gi("minsteps", 5)}
            walls, stairs, nseg = understand(b, p)
            rec = render(gray.shape, walls, stairs)
            th = [w["th_cm"] for w in walls]
            s = [f"線段 {nseg}　牆 {len(walls)}　樓梯 {len(stairs)}"]
            if th:
                s.append(f"牆厚 cm：{min(th):.0f}–{max(th):.0f}（中位 {sorted(th)[len(th)//2]:.0f}）")
                s.append(f"牆長 m：{max(w['len_m'] for w in walls):.1f} 最長")
            for st_ in stairs:
                s.append(f"樓梯：{st_['n']} 階 @ {st_['tread_cm']}cm")
            if not walls and not stairs:
                s.append("（沒有抽到任何東西 —— 放寬門檻試試）")
            return self._send(json.dumps({
                "orig": png_b64(cv2.cvtColor(cv2.normalize(gray, None, 0, 255, cv2.NORM_MINMAX),
                                             cv2.COLOR_GRAY2BGR)),
                "rec": png_b64(rec), "stats": "\n".join(s)}))
        self.send_error(404)


if __name__ == "__main__":
    if not (CASE / "01_tiles_upright").exists():
        sys.exit(f"找不到 {CASE}/01_tiles_upright/ —— 先跑 s01_ingest")
    print(f"案件：{CASE.name}")
    print(f"開啟 http://127.0.0.1:{PORT}   （Ctrl-C 結束）")
    HTTPServer(("127.0.0.1", PORT), H).serve_forever()
