"""planning/validate.py —— s06v 驗收（純程式碼閘門）

規格：v0.4 §6.2。派工單見 §13。
簽章由 §5 決定：validate(case_dir, plan) -> problems list（空 list = 通過）

退件六條（任一即退）：
  1. schema 不合法／類別不在 core/classes.py
  2. 任一 judgment 的 evidence 為空，或引用的 id 不存在於 CSV
  3. geometry 座標**無法追溯到** chain 或 measure 來源（禁止目測座標）
  4. overrides 缺 reason
  5. v2 起：上一輪任何殘差沒有出現在 residual_handling
  6. context 被改動（context 來自 02_sheets，中樞不得自行更改）

紀律：規則 2、3 要**實際去 CSV 查 id 存在性**，不是查格式。
      **不要修改 plan，不要有副作用。**
自測：附一個用 68 年案 plan_v1 樣本的自測（§13）。
      ⚠ 測資**不是** examples/plan_vN.sample.yaml —— 那是 §6.1 的格式範例，其 id
        （pair#12、chain#c003…）不存在於真實 CSV，跑 validate 必被規則 2 退件，那是正確行為。
        不可拿它當通過性自測，更不可為了讓它綠而把規則 2 降級成查格式。
        通過性測資要用 68 年案的真實 CSV 另配一份 plan_v1 —— 見 待決事項.md #8。
"""

from pathlib import Path


def validate(case_dir, plan: dict) -> list:
    raise NotImplementedError("validate 未實作（§11 第 5 步；派工單見 §13）")
