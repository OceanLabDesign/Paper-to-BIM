"""planning/tools.py —— §7.2 中樞主動工具箱（眼球轉動）

中樞拿到的是摘要，細節靠這些工具自己去看。全部**唯讀**：查得到、算得出，
但不准寫任何 CSV、不准產生 DXF（§12）。

| 工具              | 輸入 → 輸出                          |
|-------------------|--------------------------------------|
| crop_look         | 區域 → 影像（中樞親眼看）          |
| redetect          | 區域＋細參數 → 局部線段清單          |
| read_number       | 區域 → 高解析重讀（走三源）          |
| measure           | 兩線/兩點 → 精確像素距離＋換算 cm    |
| trace             | 沿線追蹤連通性 → 接合候選（摺痕斷線）|
| compare_floors    | 同位置多樓層並排影像                 |
| ask_arbiter       | → 讀數仲裁 sub-agent                 |
| ask_detective     | → 殘差偵探 sub-agent                 |

所有看圖的工具（crop_look / redetect / read_number / compare_floors）一律吃
**01_tiles_upright/**，與 s03 之後的整頁座標系同一套（裁決 §1）——
吃未轉正的 01_tiles/ 會讓中樞看到的位置與 evidence id 對不起來。

measure 的換算用 core.config.PX_PER_CM。measure 與尺寸鏈是**座標的唯二合法來源**
（戒律一：不准目測座標；validate 規則 3 會查）。
"""

from pathlib import Path

# ─────────────────────────────────────────────────────────────
# 給 LLM 的工具規格 —— planning/llm/ 的轉接器把它轉成各廠商格式
# ─────────────────────────────────────────────────────────────
# 一份宣告餵所有供應商。改這裡就好，不要在轉接器裡各寫一份。
# 參數描述刻意寫得具體（帶單位、帶合法值），因為那是模型唯一看得到的說明。
BBOX = {"type": "array", "items": {"type": "number"}, "minItems": 4, "maxItems": 4,
        "description": "整頁座標系的 [x, y, w, h]，單位 px"}

TOOL_SPECS = (
    {"name": "crop_look",
     "description": "把某個區域切出來看。你的眼睛 —— 脈絡裡只有摘要，要看細節就呼叫這支。",
     "parameters": {"type": "object", "required": ["bbox"], "properties": {
         "bbox": BBOX,
         "dpi": {"type": "integer", "default": 300, "description": "重取樣 dpi，最高 600"}}}},
    {"name": "redetect",
     "description": "用不同參數在小區域重跑線段偵測。原圖偵測不到的細線或摺痕帶可以試這支。",
     "parameters": {"type": "object", "required": ["bbox"], "properties": {
         "bbox": BBOX,
         "params": {"type": "object", "description": "覆寫 core.config 的偵測參數，只影響這次呼叫"}}}},
    {"name": "read_number",
     "description": "高解析度重讀某個數字，走 §1.2 三源投票。讀數可疑時用。",
     "parameters": {"type": "object", "required": ["bbox"], "properties": {"bbox": BBOX}}},
    {"name": "measure",
     "description": "量兩個東西之間的精確距離，回傳 px 與換算後的 cm。"
                    "**這是除了尺寸鏈以外唯一合法的座標來源（戒律一）** —— 座標不准目測。",
     "parameters": {"type": "object", "required": ["id_a", "id_b"], "properties": {
         "id_a": {"type": "string", "description": "命名空間#id，例如 line#l001"},
         "id_b": {"type": "string", "description": "同上"}}}},
    {"name": "trace",
     "description": "沿一條線追蹤連通性，回傳可能的接合候選。摺痕造成的斷線用這支接回去。",
     "parameters": {"type": "object", "required": ["line_id"], "properties": {
         "line_id": {"type": "string"}}}},
    {"name": "compare_floors",
     "description": "把同一位置在各樓層的影像並排給你看。判斷柱位是否對齊時用。",
     "parameters": {"type": "object", "required": ["bbox"], "properties": {"bbox": BBOX}}},
    {"name": "ask_arbiter",
     "description": "把一筆有疑義的讀數送給讀數仲裁 sub-agent。"
                    "它只給建議不做定案，裁不出來會回 null —— 那時就標 uncertain，不要自己選一個。",
     "parameters": {"type": "object", "required": ["read_id"], "properties": {
         "read_id": {"type": "string"}}}},
    {"name": "ask_detective",
     "description": "把一條殘差送給殘差偵探 sub-agent 調查。它只讀不寫，產出要經你放進 plan 才算數。",
     "parameters": {"type": "object", "required": ["residual_id"], "properties": {
         "residual_id": {"type": "string"}}}},
)

TOOL_NAMES = tuple(t["name"] for t in TOOL_SPECS)


def crop_look(case_dir, bbox, dpi):
    raise NotImplementedError("crop_look 未實作（§11 第 6 步）")


def redetect(case_dir, bbox, params):
    raise NotImplementedError("redetect 未實作（§11 第 6 步）")


def read_number(case_dir, bbox):
    raise NotImplementedError("read_number 未實作（§11 第 6 步）")


def measure(case_dir, id_a, id_b):
    raise NotImplementedError("measure 未實作（§11 第 6 步）")


def trace(case_dir, line_id):
    raise NotImplementedError("trace 未實作（§11 第 6 步）")


def compare_floors(case_dir, bbox):
    raise NotImplementedError("compare_floors 未實作（§11 第 6 步）")


def ask_arbiter(case_dir, read_id):
    raise NotImplementedError("ask_arbiter 未實作（§11 第 6 步）")


def ask_detective(case_dir, residual_id):
    raise NotImplementedError("ask_detective 未實作（§11 第 6 步）")
