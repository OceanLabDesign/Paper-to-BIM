"""s09_crosscheck —— 跨樓層檢查

規格：v0.4 §2（迴圈之後）、裁決 §5
輸出：**append 到 {case}/08_conflicts.csv，`source` 欄填 `cross_storey`**

要點：柱位、牆線、開口在各樓層之間對不對得起來。**對不起來是產出，不是障礙** ——
      寫進 08_conflicts.csv，不要挑一層蓋掉另一層（§12）。

08_conflicts.csv 是 append 模式、三個來源共寫（裁決 §5）：
    chain_closure  ← s05_solve（尺寸鏈加總對不上）
    plan_vN        ← orchestrator（中樞在 plan 的 conflicts 區寫的，validate 通過後併入）
    cross_storey   ← 本模組
去重是 export_review 最後統一做，本模組只管寫自己那批。
"""

from pathlib import Path

CONFLICT_SOURCE = "cross_storey"  # 裁決 §5


def run(case_dir) -> None:
    raise NotImplementedError("s09_crosscheck 未實作")
