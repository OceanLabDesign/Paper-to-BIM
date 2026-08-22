"""s07_execute —— 手：照計畫確定性執行

規格：v0.4 §8、§5
輸入：plans/plan_vN.yaml（**只讀 plan**）
輸出：{case}/out/*.dxf（ezdxf）
      ＋ {case}/07_walls.csv、{case}/07_columns.csv

07_* 由本步產出（待決 #9 的提案）：那兩個檔的內容**完全來自 plan 的 judgments**，
與 DXF 是同一次「把計畫落地」，拆成兩步只會多一次讀寫且兩邊可能不同步。
注意這不牴觸「只讀 plan」—— 那條鐵則管的是**不准讀 03/04**，不是不准寫。

★ 腦手分離的實作保證（§8 原文）：**只讀 plan，不讀任何 03/04 檔。**
  這支破了，整個設計就失效 —— 不要為了「補一下缺的線」去讀 03_lines。
  plan 裡缺的東西是中樞的問題，不是這支的問題。

確定性：同一份 plan 跑兩次要得到同一份 DXF。不要有隨機、不要有 LLM。

⚠ 裁決 §6：plan 裡任何由 core.config.ASSUMED 導出的值（thickness_src == "assumed"），
  輸出檔名必須帶 core.config.DRAFT_SUFFIX（`_draft`）。
  **粗胚 BIM 被誤當精確模型是 v0.3 風險表上的中度風險** —— 檔名是最後一道防線。
閘門：DXF 在 ArchiCAD 打得開（§11 第 5 步）。
MVP 輸出 **DXF 優先**；IFC exporter 等 ArchiCAD 四道牆往返測試通過才做（§12、§11 第 8 步）。
"""

from pathlib import Path


def execute(case_dir, plan: dict) -> None:
    raise NotImplementedError("s07_execute 未實作（§11 第 5 步）")
