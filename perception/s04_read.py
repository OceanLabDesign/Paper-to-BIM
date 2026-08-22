"""s04_read —— 三源讀取

規格：裁決 §3（v0.4 §1 補上「三源」定義，不再依賴 v0.3）
輸入：01_tiles_upright/ ＋ 03_texts.csv ＋ 03_detections.csv
輸出：{case}/04_crops/、{case}/04_readings.csv

**三源 = 三個「機制上獨立」的來源**（裁決 §3）：

  src_paddle  PaddleOCR-VL   靠字形比對      會被糊掉的字形騙
  src_vlm     VLM            靠語意與上下文  會被糊掉的字形 ＋ **幻覺** 騙
  src_geom    幾何比例        端點距離 × 比例尺，**完全不看文字** —— 會被透視/掃描變形騙

**第三源是關鍵。** 前兩者都在認字形，會被同一個模糊字一起騙 ——
兩個相關的來源等於一個來源。

投票規則（寫進 status 欄）：
  三源一致（差異在容差內）  → green   自動採用
  兩對一                    → yellow  採多數，異議者記進 suspect
  分歧、或有來源回 None      → red     人工輸入

⚠ **VLM 的失效模式**：傳統 OCR 認錯會給 `36OO` 這種一眼看得出的垃圾；
  VLM 會給你乾淨、合理、有自信、而且錯的 `3600`。
  **對矛盾偵測而言，幻覺遠比誤認致命。** 不要因為 VLM 讀起來「比較順」就加權它。

04_readings.csv 欄位（裁決 §3 定版，正式清單見 core/fields.py）：
  id,sheet_id,kind,value,unit,conf,status,
  src_paddle,src_vlm,src_geom,
  bbox_x,bbox_y,bbox_w,bbox_h,crop,
  verified_value,verified_by,verified_at,note

讀值一律走 core.io.final()：verified_value 優先於 value，兩者皆空回 None ——
**未定的值不准往下游傳**（§1）。
閘門：十張圖實驗 ≥ 目標正確率（§11 第 4 步）。
"""

from pathlib import Path

VOTE_STATUS = ("green", "yellow", "red")  # 裁決 §3
SOURCES = ("src_paddle", "src_vlm", "src_geom")


def run(case_dir: Path) -> None:
    raise NotImplementedError("s04_read 未實作（§11 第 4 步）")
