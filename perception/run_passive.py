"""run_passive —— 視神經一次跑完（s01 → s05）

規格：v0.4 §2、§5（orchestrator 開頭呼叫 run_passive(case_dir)）、裁決 §1、§2

視神經是**確定性**的：一次跑完、不迴圈、不諮詢 LLM（s02 的 VLM 只呼叫一次）。
「任一步已完成可跳過」（§5）—— 跳過判定依輸出存在與否，不是靠狀態機。

順序依裁決 §1、§2 定版：
    s01 → s01b（轉正，必須在 s02 之前）→ s02 → s02b
    → s03_lines → s03_detect → s03_texts（需 02_exclude 判 region）→ s03_elements
    → s04 → s05
"""

from pathlib import Path

from perception import (
    s01_ingest,
    s01b_orient,
    s02_layout,
    s02b_quality,
    s03_lines,
    s03_detect,
    s03_texts,
    s03_elements,
    s04_read,
    s05_solve,
)

# 順序即流程。每筆：(模組, 用來判斷「已完成」的產出)
# 產出可以是 core.case.FILES 的短名，或 core.case.DIRS 的資料夾名 —— 兩者都由
# core.case 解析，不要在這裡拼字串。每一步的鍵必須唯一，否則會誤跳過（裁決 §1 的教訓）。
STEPS = (
    (s01_ingest,    "offsets"),
    (s01b_orient,   "01_tiles_upright"),   # 轉正後的片；同時回填 offsets 的 rotation
    (s02_layout,    "sheets"),
    (s02b_quality,  "quality"),
    (s03_lines,     "lines"),
    (s03_detect,    "detections"),
    (s03_texts,     "texts"),
    (s03_elements,  "elements"),
    (s04_read,      "readings"),
    (s05_solve,     "chains"),
)


def run_passive(case_dir: Path) -> None:
    raise NotImplementedError(
        "run_passive 未實作。骨架見 STEPS；跳過判定請用 core.case 的 path()/dir_path() "
        "檢查產出存在性，不要自行拼檔名。"
    )
