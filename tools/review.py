"""tools/review.py —— 元素校對的純邏輯（裁定、重建圖、問 AI）

介面在 `tools/studio.py`，這支不開伺服器。

## 這一層在做什麼

判讀（VLM 看圖）產出的是**主張**，不是事實。這支讓人逐條裁定：
確認、退件、換類別、改文字、加註、框新元素。**AI 的原始判讀檔不動**，
裁定另存 `02_review_<tile>.json` —— 判斷錯了要能重跑、要能比對人改了什麼
（同裁決 §1 保留 `01_tiles/` 原始版的理由）。

## 訓練資料的硬閘

`status == "confirmed"` 或 `"edited"` 的框才是**人看過的**，才可以進訓練集。
AI 標了但沒人看過的（`pending`）是資料不是真值 —— 拿它訓練等於把 AI 的錯誤
燒成永久記憶。`labels()` 就是照這條規則濾的，**不要繞過它**。

## 問 AI

走 `planning/llm/claude_cli.py`（本機 Claude Code 訂閱，不吃 API 金鑰）。
送出的裁切圖**一定要把目標框出來** —— 沒標記時模型只能猜「這一處」是指哪裡，
實測它會自己挑一個然後聲明「你如果指別處請重講」，等於白問一次。
"""

import json
from datetime import datetime, timezone
from pathlib import Path

import cv2
import numpy as np

import core.classes as K

ASK_ZOOM = 2.5                   # 曬圖字小，不放大讀不出來
ASK_PAD = 90                     # 裁切時往外多帶的像素（給上下文）
STATUSES = ("pending", "confirmed", "rejected", "edited")
STATUS_ZH = {"pending": "未處理", "confirmed": "已確認",
             "rejected": "已退件", "edited": "已修改"}

COLORS = {  # BGR
    "wall": (40, 40, 40), "column": (0, 0, 0), "stair": (200, 40, 40),
    "opening": (190, 0, 150), "door": (0, 150, 0), "window": (0, 180, 180),
    "dim_line": (170, 170, 170), "dim_text": (110, 110, 110),
    "room_label": (0, 0, 0), "level_text": (200, 120, 0),
    "material_note": (0, 140, 190), "element_tag": (150, 60, 200),
    "fixture": (0, 120, 200), "hatch": (190, 190, 120),
    "calc_note": (60, 90, 200), "level_line": (200, 160, 0),
}

ASK_SYSTEM = (
    "你在協助校對台灣民國 79 年建築執照的曬圖（diazo print）掃描件。"
    "圖上手寫與印刷混雜、有摺痕與髒點。"
    "規矩三條：(1) 看不清楚就說看不清楚，不要猜一個合理的數字 —— "
    "乾淨而錯誤的答案比明顯的亂碼危險得多。"
    "(2) 對不起來的地方照實說對不起來，不要為了讓數字閉合而調整任何值。"
    "(3) 回答簡短，先講結論。"
    "圖上用洋紅色方框與四角箭頭標出的，就是要問的那個元素。"
)


def now() -> str:
    return datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")


def reviewable(case: Path) -> list:
    """有判讀結果、可以校對的片。"""
    return sorted(p.stem.replace("02_understanding_", "")
                  for p in case.glob("02_understanding_*.json"))


class Review:
    """一片的校對狀態。AI 的判讀 ＋ 人的裁定。"""

    def __init__(self, case: Path, tile: str):
        self.case, self.tile = Path(case), tile
        self.src = self.case / f"02_understanding_{tile}.json"
        self.store = self.case / f"02_review_{tile}.json"
        self.data = json.loads(self.src.read_text(encoding="utf-8"))
        meta_f = self.case / "02_regions" / "_meta.json"
        self.meta = ({m["key"]: m for m in
                      json.loads(meta_f.read_text(encoding="utf-8"))}
                     if meta_f.exists() else {})
        self.gray = cv2.imread(str(self.case / "01_tiles_upright" / f"{tile}.png"), 0)
        self.h, self.w = self.gray.shape
        self.ai = self._load_ai()
        self.s = (json.loads(self.store.read_text(encoding="utf-8"))
                  if self.store.exists()
                  else {"tile": tile, "source": self.src.name, "updated": "",
                        "rulings": {}, "added": [], "chat": []})
        self._rec = None

    def _load_ai(self) -> list:
        """區塊內的比例座標 → 整片像素座標。"""
        els = []
        for r in self.data.get("regions", []):
            m = self.meta.get(r.get("region"))
            if not m:
                continue
            for i, e in enumerate(r.get("elements", [])):
                bb = e.get("bbox") or [0, 0, 0, 0]
                ep = e.get("endpoints") or []
                els.append({
                    "id": f"{r['region']}#{i}", "region": r["region"],
                    "type": e["type"], "conf": e["confidence"],
                    "text": e.get("text", ""), "why": e.get("why", ""),
                    "box": [m["x"] + bb[0] * m["w"], m["y"] + bb[1] * m["h"],
                            m["x"] + bb[2] * m["w"], m["y"] + bb[3] * m["h"]],
                    "line": ([m["x"] + ep[0] * m["w"], m["y"] + ep[1] * m["h"],
                              m["x"] + ep[2] * m["w"], m["y"] + ep[3] * m["h"]]
                             if len(ep) == 4 else None),
                })
        return els

    def save(self):
        self.s["updated"] = now()
        self.store.write_text(json.dumps(self.s, ensure_ascii=False, indent=1),
                              encoding="utf-8")
        self._rec = None

    # ── 資料 ──────────────────────────────────────────────────────────
    def merged(self) -> list:
        out = []
        for e in self.ai:
            r = self.s["rulings"].get(e["id"], {})
            m = dict(e)
            m["status"] = r.get("status", "pending")
            for k in ("type", "text", "box", "note"):
                if r.get(k) is not None:
                    m[k] = r[k]
            m.setdefault("note", "")
            m["by"] = r.get("by", "ai")
            out.append(m)
        for a in self.s["added"]:
            out.append({**a, "region": "human", "conf": "確定", "why": "人工新增",
                        "line": a.get("line"),
                        "status": a.get("status", "confirmed"), "by": "human"})
        return out

    def rule(self, eid, status, type_=None, text="", note=""):
        if status == "pending":
            self.s["rulings"].pop(eid, None)
        else:
            self.s["rulings"][eid] = {"status": status, "type": type_,
                                      "text": text, "note": note,
                                      "by": "human", "at": now()}
        self.save()

    def add(self, box, type_, text="", note="人工新增"):
        a = {"id": f"human#{len(self.s['added']) + 1}", "type": type_, "box": box,
             "text": text, "note": note, "status": "confirmed",
             "by": "human", "at": now()}
        self.s["added"].append(a)
        self.save()
        return a

    def labels(self) -> list:
        """可以進訓練集的框 —— **只有人看過的**。見檔頭「訓練資料的硬閘」。"""
        return [e for e in self.merged()
                if e["status"] in ("confirmed", "edited")]

    def stats(self) -> dict:
        m = self.merged()
        c = {k: sum(1 for e in m if e["status"] == k) for k in STATUSES}
        return {"total": len(m), **c, "labels": len(self.labels())}

    # ── 重建圖 ────────────────────────────────────────────────────────
    def reconstruction(self, scale=0.30) -> bytes:
        """只畫人沒退掉的元素 —— 這就是「確認後才畫」的預覽。"""
        if self._rec is not None:
            return self._rec
        c = np.full((self.h, self.w, 3), 255, np.uint8)
        for e in self.merged():
            if e["status"] == "rejected":
                continue
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
                for i in range(1, 14):
                    x = int(b[0] + i * (b[2] - b[0]) / 14)
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
        small = cv2.resize(c, (0, 0), fx=scale, fy=scale,
                           interpolation=cv2.INTER_AREA)
        self._rec = cv2.imencode(".png", small)[1].tobytes()
        return self._rec

    def original(self, scale=0.30) -> bytes:
        g = cv2.normalize(self.gray, None, 0, 255, cv2.NORM_MINMAX)
        small = cv2.resize(g, (0, 0), fx=scale, fy=scale,
                           interpolation=cv2.INTER_AREA)
        return cv2.imencode(".png", small)[1].tobytes()

    # ── 問 AI ─────────────────────────────────────────────────────────
    def crop(self, box, pad=ASK_PAD, zoom=ASK_ZOOM) -> bytes:
        """裁出該元素附近並放大，**並且把目標框出來**（見檔頭）。"""
        x0 = max(0, int(box[0]) - pad); y0 = max(0, int(box[1]) - pad)
        x1 = min(self.w, int(box[2]) + pad); y1 = min(self.h, int(box[3]) + pad)
        if x1 - x0 < 8 or y1 - y0 < 8:
            x0, y0, x1, y1 = 0, 0, self.w, self.h
        c = cv2.cvtColor(cv2.normalize(self.gray[y0:y1, x0:x1], None, 0, 255,
                                       cv2.NORM_MINMAX), cv2.COLOR_GRAY2BGR)
        c = cv2.resize(c, (0, 0), fx=zoom, fy=zoom, interpolation=cv2.INTER_CUBIC)
        a = (int((box[0] - x0) * zoom), int((box[1] - y0) * zoom),
             int((box[2] - x0) * zoom), int((box[3] - y0) * zoom))
        cv2.rectangle(c, (a[0], a[1]), (a[2], a[3]), (255, 0, 255), 3)
        for px, py, dx, dy in ((a[0], a[1], -1, -1), (a[2], a[1], 1, -1),
                               (a[0], a[3], -1, 1), (a[2], a[3], 1, 1)):
            cv2.line(c, (px + dx * 34, py + dy * 34), (px + dx * 6, py + dy * 6),
                     (255, 0, 255), 3)
        return cv2.imencode(".png", c)[1].tobytes()

    def ask(self, prompt: str, eid=None, llm=None) -> dict:
        from planning.llm.base import text as _t
        from planning.llm.registry import get_provider
        llm = llm or get_provider("claude_cli", resume=True, timeout=300)
        e = next((x for x in self.merged() if x["id"] == eid), None)
        content = [_t(prompt)]
        if e:
            content.append({"type": "image", "media_type": "image/png",
                            "data": self.crop(e["box"])})
        r = llm.complete([{"role": "user", "content": content}], system=ASK_SYSTEM)
        out = {"text": r["content"][0]["text"], "usage": r["usage"],
               "cost": round(llm.last_cost_usd, 4)}
        self.s["chat"] += [{"role": "user", "text": prompt, "about": eid, "at": now()},
                           {"role": "ai", "text": out["text"],
                            "meta": f"${out['cost']}", "at": now()}]
        self.save()
        return out


CLASS_LIST = [[n, z] for n, z, _t in K.CLASSES]
