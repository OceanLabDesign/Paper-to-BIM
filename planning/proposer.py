"""planning/proposer.py —— s06 中樞

規格：v0.4 §7。產出是**一份繪圖計畫（plans/plan_vN.yaml），不是動作**。

簽章由 §5 的迴圈決定：
    propose_plan(case_dir, version=n, residuals=prev, rejected=problems) -> plan dict

§0.3 的建造紀律：**先做骨架與假中樞（回固定計畫），接通迴圈後才接真 LLM。**
§11 第 5 步先於第 6 步是刻意的 —— 真中樞接上時只剩一個變因。

中樞不准做的事（§12）：
  - 直接寫 CSV（含 03_elements 的 status 回寫 —— 那是 orchestrator 的事）
  - 直接呼叫 ezdxf
  - 決定要不要再跑一輪
  - 拿到 649 條線段那種原始資料 —— 脈絡是摘要，由 planning/context.py 依 §7.1 節食後餵進來，
    細節要自己呼叫 planning/tools.py 的工具箱（§7.2）去看
"""

from pathlib import Path


def propose_plan(case_dir, version: int, residuals=None, rejected=None) -> dict:
    """回傳 plan dict（結構見 core/plan_schema.py／§6.1），並寫出 plans/plan_vN.yaml。

    residuals：上一輪 s08 的殘差（v1 為 None）
    rejected ：同輪驗收退件的 problems，非 None 表示這是退件重寫（同輪一次為限）
    """
    raise NotImplementedError("真中樞未實作（§11 第 6 步）；第 5 步請用 planning/fake_proposer.py")
