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
