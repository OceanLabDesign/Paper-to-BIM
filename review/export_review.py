"""export_review —— 校對介面（Excel 先頂）

規格：v0.4 §5（迴圈結束後呼叫）、§1、裁決 §5
輸入：08_conflicts.csv（三來源已 append 完）＋ 低信心／uncertain 的判斷
輸出：黃紅 ＋ 衝突 → Excel

**去重在這裡做，而且只在這裡做**（裁決 §5）：
    同一組 involved_ids 只留 severity 最高的那筆。
上游三支（s05_solve / orchestrator / s09_crosscheck）各自 append，不必先協調。

原則（§1）：一開始**不上資料庫、不做網頁校對（Excel 先頂）、不追求全自動**。
這是「不確定往上傳不往下傳」的終點 —— 攤給人看，不是自己吞掉。
"""

from pathlib import Path


def export_review(case_dir) -> None:
    raise NotImplementedError("export_review 未實作（§11 第 5 步）")
