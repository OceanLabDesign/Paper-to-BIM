"""s08_compare —— 對照：像素重疊算術

規格：v0.4 §8、§5
輸入：plan ＋ {case}/01_tiles_upright/（**轉正後** —— 投影回像素要跟 s03 同一個座標系）
輸出：{case}/plans/residuals_vN.csv（回饋給中樞）

要點：把 judgments 幾何**投影回像素**，算覆蓋率與未解釋粗線。
      殘差落在 crease 區者自動註記（quality_zone 來自 02_quality）。

純算術，沒有 LLM。這支只**報告**殘差，不判斷該不該收工 ——
終止條件是 orchestrator.residuals_all_handled() 的事（§5 鐵則）。
"""

from pathlib import Path


def render_compare(case_dir, plan: dict):
    """回傳這一輪的殘差（同時寫出 residuals_vN.csv），供下一輪中樞使用。"""
    raise NotImplementedError("s08_compare 未實作（§11 第 5 步）")
