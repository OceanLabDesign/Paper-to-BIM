"""s03_lines —— 線段偵測

規格：v0.4 §8、參數見 core/config.py（§10）
輸入：{case}/01_tiles_upright/*.png ＋ {case}/01_offsets.csv
      （**必須吃轉正後的片**：offsets 的 x/y 已由 s01b 依 rotation 重算過，
        配未轉正的片會整片偏掉 —— 裁決 §1）
輸出：{case}/03_lines.csv

要點：**自適應二值化 (ADAPTIVE_BLOCK, ADAPTIVE_C) = (31, 12)，禁用 Otsu。**
      座標經 offsets 轉為**整頁座標系**後才寫檔（不要留片內座標）。
閘門：疊圖目視 —— 牆心線壓真牆（§11 第 3 步）。

禁：不要重新調參。那組數字是曬圖陰影下活下來的實測值。
"""

from pathlib import Path


def run(case_dir: Path) -> None:
    raise NotImplementedError("s03_lines 未實作（§11 第 3 步）")
