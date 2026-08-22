"""殘差偵探 sub-agent

規格：v0.4 §7.4
入：一條殘差 ＋ 工具箱（**唯讀**）
出：{建議, 證據, 信心}

紅線（§7.4 原文）：**產出只能進 plan 的 uncertain/judgments 並經驗收，
不得直接寫任何 CSV。**
"""

from pathlib import Path


def investigate(case_dir, residual_id) -> dict:
    raise NotImplementedError("殘差偵探未實作（§11 第 6 步）")
