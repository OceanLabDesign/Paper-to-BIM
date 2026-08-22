"""s03_texts —— 全圖文字擷取

規格：裁決 §2（v0.4 §8 漏了這支，v0.4.1 補上）
輸入：{case}/01_tiles_upright/ ＋ {case}/02_exclude.csv
輸出：{case}/03_texts.csv

要點：
  - PaddleOCR-VL 跑**每一片全圖**，取出所有文字 + bbox（不是只挑尺寸標註）
  - 座標經 01_offsets.csv 轉為整頁座標系
  - `region` 欄依 02_exclude 判定：body / title_block / schedule

順序：排在 s02 之後 —— region 判定需要 02_exclude 才做得出來（裁決 §2）。
下游：s04_read 的 src_paddle 源、s02 讀出的標題欄線索交叉比對。
"""

from pathlib import Path

REGIONS = ("body", "title_block", "schedule")  # 裁決 §2


def run(case_dir: Path) -> None:
    raise NotImplementedError("s03_texts 未實作（§11 第 3 步）")
