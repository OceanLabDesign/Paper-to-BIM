"""crease_repair 的可執行部分 —— 找出摺痕帶裡的斷線候選

**唯讀**：只回報候選，不改任何 CSV、不寫 plan。
判定該不該接是中樞的事（見同資料夾的 SKILL.md），不是這支的事。
"""


def run(case_dir, sheet_id=None, max_gap_px=None):
    """回傳 [{line_a, line_b, gap_px, angle_diff_deg, quality_zone}]。

    做法：取 02_quality 中 level == "crease" 的區塊，
    找落在其中、共線且首尾相望的 03_lines 線段對。
    """
    raise NotImplementedError("crease_repair.run 未實作（§11 第 6 步）")
