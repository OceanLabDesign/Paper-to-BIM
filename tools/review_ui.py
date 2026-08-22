"""tools/review_ui.py —— 理解結果的校對介面

`python3 tools/review_ui.py` → 開 http://127.0.0.1:8711

給人**校對 AI 理解了什麼**的工具。不是給 AI 用的，是給建築師用的：
每一筆判斷都看得到「它憑什麼這樣判」（why 欄）與信心，點一下就在原圖上框出來。

這正是規格 §1「不確定往上傳不往下傳」的終點 —— 攤給人看，不是自己吞掉。
只用標準函式庫的 http.server，不加相依。
"""

import base64
import json
import sys
import urllib.parse
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.dont_write_bytecode = True

import cv2                                                        # noqa: E402
import numpy as np                                                # noqa: E402

CASE = ROOT / "cases" / "79-B37001_七賢二路"
TILE = "p03"
PORT = 8711

COLORS = {  # BGR
    "wall": (40, 40, 40), "column": (0, 0, 0), "stair": (200, 40, 40),
    "opening": (190, 0, 150), "door": (0, 150, 0), "window": (0, 180, 180),
    "dim_line": (170, 170, 170), "dim_text": (110, 110, 110),
    "room_label": (0, 0, 0), "level_text": (200, 120, 0),
    "material_note": (0, 140, 190), "element_tag": (150, 60, 200),
    "fixture": (0, 120, 200), "hatch": (190, 190, 120),
}
ZH = {"wall": "牆", "column": "柱", "stair": "樓梯", "opening": "開口／井道",
      "door": "門", "window": "窗", "dim_line": "尺寸線", "dim_text": "尺寸數字",
      "room_label": "室名", "level_text": "標高", "material_note": "材料註記",
      "element_tag": "元件編號", "fixture": "設備", "hatch": "剖面填充"}


def load():
    d = json.loads((CASE / f"02_understanding_{TILE}.json").read_text(encoding="utf-8"))
    meta = {m["key"]: m for m in json.loads(
        (CASE / "02_regions" / "_meta.json").read_text(encoding="utf-8"))}
    els = []
    for r in d["regions"]:
        m = meta.get(r["region"])
        if not m:
            continue
        for i, e in enumerate(r.get("elements", [])):
            bb = e.get("bbox") or [0, 0, 0, 0]
            ep = e.get("endpoints") or []
            box = [m["x"] + bb[0] * m["w"], m["y"] + bb[1] * m["h"],
                   m["x"] + bb[2] * m["w"], m["y"] + bb[3] * m["h"]]
            line = ([m["x"] + ep[0] * m["w"], m["y"] + ep[1] * m["h"],
                     m["x"] + ep[2] * m["w"], m["y"] + ep[3] * m["h"]]
                    if len(ep) == 4 else None)
            els.append({"id": f"{r['region']}#{i}", "region": r["region"],
                        "type": e["type"], "conf": e["confidence"],
                        "text": e.get("text", ""), "why": e.get("why", ""),
                        "box": box, "line": line})
    return d, els


DATA, ELS = load()
GRAY = cv2.imread(str(CASE / "01_tiles_upright" / f"{TILE}.png"), 0)
H, W = GRAY.shape
SCALE = 0.30


def render_reconstruction():
    c = np.full((H, W, 3), 255, np.uint8)
    for e in ELS:
        col = COLORS.get(e["type"], (120, 120, 120))
        b = [int(v) for v in e["box"]]
        if e["type"] == "wall" and e["line"]:
            a = [int(v) for v in e["line"]]
            w = 24 if e["conf"] == "確定" else 14
            cv2.line(c, (a[0], a[1]), (a[2], a[3]), col, w)
            cv2.line(c, (a[0], a[1]), (a[2], a[3]), (255, 255, 255), max(1, w - 9))
            cv2.line(c, (a[0], a[1]), (a[2], a[3]), col, 2)
        elif e["type"] == "stair":
            cv2.rectangle(c, (b[0], b[1]), (b[2], b[3]), col, 4)
            n = 14
            for i in range(1, n):
                x = int(b[0] + i * (b[2] - b[0]) / n)
                cv2.line(c, (x, b[1]), (x, b[3]), (210, 130, 130), 3)
        elif e["type"] == "opening":
            cv2.rectangle(c, (b[0], b[1]), (b[2], b[3]), col, 4)
            cv2.line(c, (b[0], b[1]), (b[2], b[3]), col, 3)
            cv2.line(c, (b[2], b[1]), (b[0], b[3]), col, 3)
        elif e["type"] == "door":
            r = max(8, min(b[2] - b[0], b[3] - b[1]))
            cv2.ellipse(c, (b[0], b[3]), (r, r), 0, -90, 0, col, 4)
            cv2.line(c, (b[0], b[3]), (b[0] + r, b[3]), col, 4)
        elif e["type"] == "dim_line" and e["line"]:
            a = [int(v) for v in e["line"]]
            cv2.line(c, (a[0], a[1]), (a[2], a[3]), col, 3)
            for p in ((a[0], a[1]), (a[2], a[3])):
                cv2.line(c, (p[0] - 11, p[1] + 11), (p[0] + 11, p[1] - 11), col, 3)
        else:
            cv2.rectangle(c, (b[0], b[1]), (b[2], b[3]), col, 3)
    return c


def b64(img):
    small = cv2.resize(img, (0, 0), fx=SCALE, fy=SCALE, interpolation=cv2.INTER_AREA)
    return base64.b64encode(cv2.imencode(".png", small)[1]).decode()


ORIG_B64 = b64(cv2.cvtColor(cv2.normalize(GRAY, None, 0, 255, cv2.NORM_MINMAX),
                            cv2.COLOR_GRAY2BGR))
REC_B64 = b64(render_reconstruction())

HTML = """<!doctype html><meta charset=utf-8><title>理解校對</title>
<style>
 *{box-sizing:border-box} body{margin:0;font:13px/1.6 -apple-system,"PingFang TC",sans-serif;
  background:#101215;color:#dde;display:flex;height:100vh;overflow:hidden}
 #stage{flex:1;position:relative;overflow:auto;background:#0a0b0d}
 #canvasWrap{position:relative;display:inline-block;margin:12px}
 #base{display:block}
 #hl{position:absolute;inset:0;pointer-events:none}
 #bar{position:sticky;top:0;z-index:9;background:#181b20;padding:8px 12px;display:flex;
  gap:8px;align-items:center;border-bottom:1px solid #2a2f37}
 .btn{padding:5px 11px;background:#232830;border:1px solid #333a44;color:#cde;border-radius:5px;cursor:pointer}
 .btn.on{background:#0a84ff;border-color:#0a84ff;color:#000;font-weight:600}
 #side{width:400px;background:#15181d;border-left:1px solid #2a2f37;display:flex;flex-direction:column}
 #side h3{margin:0;padding:12px;font-size:14px;color:#0a84ff;border-bottom:1px solid #2a2f37}
 #filters{padding:9px 12px;border-bottom:1px solid #2a2f37;display:flex;flex-wrap:wrap;gap:5px}
 .chip{padding:3px 9px;background:#232830;border:1px solid #333a44;border-radius:11px;
  cursor:pointer;font-size:11px}
 .chip.on{background:#0a84ff;color:#000;border-color:#0a84ff}
 #list{flex:1;overflow-y:auto}
 .row{padding:8px 12px;border-bottom:1px solid #1e2229;cursor:pointer}
 .row:hover{background:#1c2027} .row.sel{background:#0a84ff22;border-left:3px solid #0a84ff}
 .t{font-weight:600} .c{float:right;font-size:11px;padding:1px 7px;border-radius:9px}
 .c.確定{background:#0a5} .c.可能{background:#a70} .c.不確定{background:#a33}
 .why{color:#8a929c;font-size:11px;margin-top:3px}
 #note{padding:11px;background:#0d0f12;border-top:1px solid #2a2f37;font-size:11px;
  color:#9aa;max-height:34vh;overflow-y:auto;white-space:pre-wrap}
</style>
<div id=stage>
  <div id=bar>
    <span class="btn on" id=b_orig onclick=setView('orig')>原掃描</span>
    <span class="btn" id=b_rec onclick=setView('rec')>理解後重建</span>
    <span class="btn" id=b_both onclick=setView('both')>疊合</span>
    <span style=margin-left:auto;color:#7a828c id=count></span>
  </div>
  <div id=canvasWrap><img id=base><canvas id=hl></canvas></div>
</div>
<div id=side>
  <h3>理解校對　p03 屋頂層平面圖</h3>
  <div id=filters></div>
  <div id=list></div>
  <div id=note></div>
</div>
<script>
let D=null,view='orig',sel=null,off={};
fetch('/data').then(r=>r.json()).then(d=>{D=d;init()});
function init(){
  const types=[...new Set(D.els.map(e=>e.type))];
  types.forEach(t=>off[t]=false);
  filters.innerHTML=types.map(t=>`<span class="chip on" data-t="${t}"
    onclick="tog('${t}',this)">${D.zh[t]||t} ${D.els.filter(e=>e.type==t).length}</span>`).join('');
  ['確定','可能','不確定'].forEach(c=>off['conf:'+c]=false);
  filters.innerHTML+=' | '+['確定','可能','不確定'].map(c=>`<span class="chip on" data-t="conf:${c}"
    onclick="tog('conf:${c}',this)">${c}</span>`).join('');
  note.textContent='交叉檢查\\n\\n'+
    ['missing','inconsistent','suspicious'].map(k=>
      (D.check[k]||[]).map(x=>'• '+x).join('\\n\\n')).filter(Boolean).join('\\n\\n')+
    '\\n\\n【總評】\\n'+(D.check.verdict||'');
  setView('orig'); draw();
}
function tog(k,el){off[k]=!off[k];el.classList.toggle('on');draw()}
function vis(e){return !off[e.type] && !off['conf:'+e.conf]}
function setView(v){view=v;
  for(const k of ['orig','rec','both'])document.getElementById('b_'+k).classList.toggle('on',k==v);
  base.src='data:image/png;base64,'+(v=='rec'?D.rec:D.orig);
  base.style.opacity = v=='both'?0.45:1;
  base.onload=()=>{hl.width=base.width;hl.height=base.height;draw()}}
function draw(){
  if(!D)return;
  const shown=D.els.filter(vis); count.textContent=shown.length+' / '+D.els.length+' 個元素';
  list.innerHTML=shown.map((e,i)=>`<div class="row${sel===e.id?' sel':''}" onclick="pick('${e.id}')">
    <span class=t>${D.zh[e.type]||e.type}</span><span class="c ${e.conf}">${e.conf}</span>
    ${e.text?`<div style="color:#0a84ff">「${e.text}」</div>`:''}
    <div class=why>${e.why||''}</div></div>`).join('');
  const g=hl.getContext('2d'); g.clearRect(0,0,hl.width,hl.height);
  const s=D.scale;
  for(const e of shown){
    const b=e.box.map(v=>v*s);
    g.strokeStyle = e.id===sel?'#0a84ff':'rgba(255,90,60,.55)';
    g.lineWidth = e.id===sel?3:1;
    g.strokeRect(b[0],b[1],b[2]-b[0],b[3]-b[1]);
    if(view=='both'&&e.line){const l=e.line.map(v=>v*s);
      g.beginPath();g.moveTo(l[0],l[1]);g.lineTo(l[2],l[3]);
      g.strokeStyle='rgba(0,200,120,.8)';g.lineWidth=2;g.stroke()}
  }
}
function pick(id){sel=(sel===id?null:id);draw();
  const e=D.els.find(x=>x.id===id); if(!e)return;
  const b=e.box.map(v=>v*D.scale);
  stage.scrollTo({left:b[0]-stage.clientWidth/2,top:b[1]-stage.clientHeight/2,behavior:'smooth'})}
</script>"""


class H(BaseHTTPRequestHandler):
    def log_message(self, *a):
        pass

    def do_GET(self):
        u = urllib.parse.urlparse(self.path)
        if u.path == "/":
            body, ctype = HTML.encode(), "text/html; charset=utf-8"
        elif u.path == "/data":
            body = json.dumps({"els": ELS, "orig": ORIG_B64, "rec": REC_B64,
                               "scale": SCALE, "zh": ZH,
                               "check": DATA.get("check", {})}).encode()
            ctype = "application/json"
        else:
            return self.send_error(404)
        self.send_response(200)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)


if __name__ == "__main__":
    print(f"元素 {len(ELS)} 個｜圖 {TILE}　{W}×{H}px")
    print(f"開啟 http://127.0.0.1:{PORT}   （Ctrl-C 結束）")
    HTTPServer(("127.0.0.1", PORT), H).serve_forever()
