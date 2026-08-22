"""planning/fake_proposer.py —— 假中樞（回固定計畫）

規格：v0.4 §0.3、§11 第 5 步。

用途：**迴圈、驗收、執行、對照全部先用假中樞驗通**，真中樞接上時只剩一個變因。
簽章與 proposer.propose_plan() 完全一致，可直接替換。

假中樞回的是寫死的 plan：68 年案手寫計畫，結構照 §6.1（格式參考
examples/plan_vN.sample.yaml），但 **id 必須是真實 CSV 裡查得到的** ——
範例檔的 id 是假的，直接拿來用會被 validate 規則 2 退件。
它必須**通得過 validate 六條** —— 不然驗不到迴圈，只驗到退件。
"""

from pathlib import Path


def propose_plan(case_dir, version: int, residuals=None, rejected=None) -> dict:
    raise NotImplementedError("fake_proposer 未實作（§11 第 5 步，第一個該做的）")
