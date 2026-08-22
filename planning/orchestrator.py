"""planning/orchestrator.py —— 全系統唯一的流程控制器

規格：v0.4 §5。迴圈骨架逐字照抄，不要重排、不要加分支。

**鐵則（§5）：`for` 迴圈、終止條件、退件，全在這支程式碼；中樞永遠只被呼叫。**
§12 明列不准做的事：把迴圈控制交給 agent（含「讓中樞自己決定要不要再跑一輪」）。

v0.3 說「不要大 main()」—— 本檔是唯一的例外（§1）。其餘各步仍可單獨執行。
"""

from pathlib import Path

from core.config import MAX_ITER  # §10。§5 骨架寫 MAX_ITER = 3，同值，取單一來源
from perception.run_passive import run_passive          # s01–s05
from planning.proposer import propose_plan                        # s06
from planning.validate import validate                  # s06v
from execution.s07_execute import execute                # s07
from execution.s08_compare import render_compare         # s08
from review.export_review import export_review

# 裁決 §5：中樞寫進 08_conflicts.csv 的 source 值。
# ⚠ 裁決表格寫的是 `plan_vN` —— 另兩個來源（chain_closure / cross_storey）都是固定字串，
#   這個帶 N 應是要記下「哪一版 plan 寫的」，故用樣板。若你要的是字面 "plan_vN"，改這行。
#   見 待決事項.md #10。
CONFLICT_SOURCE_FMT = "plan_v{version}"


def run_case(case_dir):
    run_passive(case_dir)                    # s01–s05，任一步已完成可跳過
    prev = None
    for n in range(1, MAX_ITER + 1):
        plan = propose_plan(case_dir, version=n, residuals=prev)   # s06
        problems = validate(case_dir, plan)                  # s06v
        if problems:
            plan = propose_plan(case_dir, version=n, residuals=prev,
                                rejected=problems)                  # 退件重寫，同輪一次為限
            problems = validate(case_dir, plan)
            if problems:
                mark_stuck(case_dir, problems); break
        apply_plan_status(case_dir, plan)      # ★ 裁決 §4：把 plan 的裁定回寫
                                               #   03_detections / 03_elements 的
                                               #   status 欄 → adopted/rejected/uncertain
        execute(case_dir, plan)                              # s07
        prev = render_compare(case_dir, plan)                # s08 → residuals_vN.csv
        if residuals_all_handled(plan, prev):                # 程式碼判定，不是 agent 自稱
            break
    export_review(case_dir)                                  # 黃紅＋衝突 → Excel


# ⚠ 待決事項.md #7：「已修／已報告」的具體判準（residuals_vN.csv 憑哪一欄判定、
#   要不要比對 plan.conflicts/uncertain 的 id、覆蓋率門檻）§2/§5/§8 都沒定。
def apply_plan_status(case_dir, plan) -> None:
    """把 plan 的裁定回寫 03_detections / 03_elements 的 status 欄（§9、裁決 §4）。

    proposed → adopted / rejected / uncertain。**獨立一步，必須在 validate 之後、
    execute 之前**：s07_execute 只准讀 plan（腦手分離鐵則），不能讓它順手回寫。

    同時把 plan 的 conflicts 區 append 進 08_conflicts.csv，`source` 欄填 `plan_vN`
    （裁決 §5：conflicts 逐步累積，不要留到最後統一收集）。
    """
    raise NotImplementedError("apply_plan_status 未實作（§11 第 5 步）")


def residuals_all_handled(plan, residuals) -> bool:
    """終止條件：「殘差皆已修或已報告」（§2）。

    **由程式碼判定，不是 agent 自稱**（§5）。
    引數只有「這一輪」的 plan_vN 與其執行後 s08 算出的 residuals_vN —— 逐條看每筆殘差
    是否已修（judgments 已覆蓋）或已報告（已落在 plan 的 conflicts / uncertain），
    兩者皆非就回 False，由 orchestrator 再跑一輪。

    注意：「下一輪 plan 的 residual_handling 有沒有逐條回應」是 §6.2 規則 5，
    那是 validate 的退件條件（見 planning/validate.py），**不在本函式**，也拿不到那份資料。
    殘差處理只有 revise 或 report（§12），不准為了收斂蓋掉一邊。
    """
    raise NotImplementedError("residuals_all_handled 未實作（§11 第 5 步）")


def mark_stuck(case_dir, problems) -> None:
    """同一輪退件兩次仍不過 → 記進 log.csv 並中止迴圈（§5）。不要重跑第三次。"""
    raise NotImplementedError("mark_stuck 未實作（§11 第 5 步）")


if __name__ == "__main__":
    import sys
    run_case(Path(sys.argv[1]))
