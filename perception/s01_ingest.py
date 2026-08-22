"""s01_ingest —— PDF 拆片（免拼接）

規格：v0.4 §8、裁決 §1、§11 第 2 步
輸入：{case}/00_raw/*.pdf
輸出：{case}/01_tiles/*.png（各片**原始解析度、未轉正**）、{case}/01_offsets.csv

要點：**用 PyMuPDF 讀每個影像 XObject 的放置矩陣** —— Illustrator 拼的檔案，
      偏移量就寫在 PDF 裡，不用重新對位、不要做特徵點拼接。

01_offsets.csv 欄位（裁決 §1 定版，正式清單見 core/fields.py）：
    tile_id,page,x,y,w,h,rotation,upright_file
    p01_t01,1,0,0,3507,4960,180,01_tiles_upright/p01_t01.png

**本步 `rotation` 與 `upright_file` 兩欄留空** —— 那是 s01b 的事。

禁：不要在這裡轉正、不要降解析度。01_tiles/ 是可追溯的原始版，永不就地覆蓋。
"""

from pathlib import Path


def run(case_dir: Path) -> None:
    raise NotImplementedError("s01_ingest 未實作（§11 第 2 步）")
