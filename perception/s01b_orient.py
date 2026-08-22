"""s01b_orient —— 方向偵測與轉正

規格：裁決 §1（**v0.4 §8 說它更新 02_sheets.orientation 是寫錯的**，v0.4.1 已修）
輸入：{case}/01_tiles/*.png ＋ {case}/01_offsets.csv
輸出：填 01_offsets.csv 的 `rotation` 與 `upright_file` 欄
      ＋ {case}/01_tiles_upright/*.png（轉正後）

**本步不碰 02_sheets.csv** —— 02_sheets 是 s02 產出的，s02 會把 rotation 抄進
orientation 欄當紀錄。

要點：偵測 0/90/180/270，用文字方向投票。
實測：**68 年案第 1 頁是 180°** —— 這是第一筆迴歸測試。

⚠ **轉正會改變 tile 在頁座標系的 offset。** 填 rotation 時**必須同步重算 x/y**，
  否則下游（s03 線段轉整頁座標）會整片偏掉。這是本模組最容易錯的地方。

為什麼方向必須排在版面之前（裁決 §1）：s02 要 VLM 讀標題欄的字，
圖是顛倒的，VLM 讀出來的東西不能用。
為什麼保留 01_tiles/ 原始版：可追溯 —— 轉正判斷錯了要能重跑，不能就地覆蓋。
"""

from pathlib import Path

from core.fields import OFFSETS   # tile_id,page,x,y,w,h,rotation,upright_file

ROTATIONS = (0, 90, 180, 270)    # 裁決 §1


def run(case_dir: Path) -> None:
    raise NotImplementedError("s01b_orient 未實作（§11 第 3 步）")
