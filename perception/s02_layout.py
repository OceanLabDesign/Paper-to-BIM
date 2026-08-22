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


def run(case_dir: Path) -> None:
    raise NotImplementedError("s02_layout 未實作（§11 第 3 步）")
