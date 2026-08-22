"""core/plan_schema.py —— 繪圖計畫的結構定義與驗收規則

★ 契約三件套之一。規格 §4 原規定是「專案負責人親手寫，程式只能引用」——
  本檔由 Claude Code 依負責人指派代擬。**尚未定版，需負責人逐項確認。**

本檔只定義「結構與規則是什麼」；**檢查邏輯寫在 planning/validate.py**，
兩者分開是為了讓規則可以被讀、被列印、被拿去寫測試，而不是埋在 if 裡。

標記：【定版】= 規格 §6 逐字；【草案】= 規格只給了範例，鍵名由本檔代擬。
"""

# ─────────────────────────────────────────────────────────────
# §6.1 結構 —— plan_vN.yaml 的七個區塊
# ─────────────────────────────────────────────────────────────
# 【定版】規格 §6.1
SECTIONS = ("meta", "context", "judgments", "overrides",
            "conflicts", "uncertain", "residual_handling")

# meta 必填；v1 的 based_on 填 None
META_KEYS = ("case", "sheet", "version", "based_on")

# context 來自 02_sheets，**中樞不得自行更改**（§6.2 規則 6 就是查這五個鍵）
CONTEXT_KEYS = ("kind", "floor", "scale", "unit", "orientation")

# 每筆 judgment 的鍵。type 只能用 core/classes.py；evidence 至少一個。
JUDGMENT_KEYS = ("id", "type", "geometry", "evidence", "confidence", "note")
JUDGMENT_REQUIRED = ("id", "type", "geometry", "evidence")

# 【草案】geometry 是 dict：幾何走 WKT，其餘是屬性。
# 規格 §6.1 範例：{ axis_wkt: "LINESTRING(0 0, 806 0)", thickness: 24 }
GEOMETRY_WKT_KEYS = ("axis_wkt", "outline_wkt", "bbox_wkt", "point_wkt")

OVERRIDE_KEYS = ("label", "action", "reason")
OVERRIDE_REQUIRED = ("label", "action", "reason")        # reason 缺 → §6.2 規則 4
OVERRIDE_ACTIONS = ("reject", "accept", "revise")        # 【草案】§6.1 只出現過 reject

CONFLICT_KEYS = ("kind", "detail", "involved")
UNCERTAIN_KEYS = ("judgment", "reason", "basis")

# v2 起必填：逐條回應上一輪殘差
RESIDUAL_KEYS = ("residual", "action", "detail")
RESIDUAL_ACTIONS = ("revise", "report")   # 【定版】§6.1、§12：只有這兩種，不准第三種

# 一筆 judgment 至少要有幾個 evidence（§6.2 規則 2）
MIN_EVIDENCE = 1


# ─────────────────────────────────────────────────────────────
# §6.2 驗收規則 —— 任一成立即退件
# ─────────────────────────────────────────────────────────────
# 【定版】規格 §6.2 六條，逐字。validate 回傳的 problems 每筆帶 rule 編號，
# 讓退件重寫時中樞知道是哪一條掛掉（§5 的 rejected 參數）。
REJECT_RULES = (
    (1, "schema 不合法／類別不在 classes.py"),
    (2, "任一 judgment 的 evidence 為空，或引用的 id 不存在於 CSV"),
    (3, "geometry 座標無法追溯到 chain 或 measure 來源（禁止目測座標）"),
    (4, "overrides 缺 reason"),
    (5, "v2 起：上一輪任何殘差沒有出現在 residual_handling"),
    (6, "context 被改動"),
)

# 規則 5 從第幾版開始查
RESIDUAL_HANDLING_FROM_VERSION = 2

# 規則 2、3 的實作要點（寫成常數是為了讓 validate 不會漏）：
#   規則 2：evidence 的每個字串形如 `命名空間#id`，前綴查 core.fields.EVIDENCE_NS
#           解析到「哪個 CSV 的哪個 id 欄」，**實際去該 CSV 查 id 存在**，不是查格式。
#   規則 3：geometry 的每個 *_wkt 座標，必須有一筆 evidence 的命名空間屬於
#           core.fields.COORD_SOURCES（chain / measure）。目測座標一律退。
#           —— measure 的結果不落 CSV，中樞要把它寫進 note 或以 measure#… 形式引用；
#              這條的落地方式**待負責人確認**（見 待決事項.md）。


def problem(rule: int, where: str, detail: str) -> dict:
    """validate 回傳的 problems 統一長這樣（程式用 dict 不用 dataclass，v0.3 原則）。"""
    return {"rule": rule, "where": where, "detail": detail}
