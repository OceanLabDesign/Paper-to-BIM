"""core/plan_schema.py —— 繪圖計畫的結構定義與驗收規則

★ 契約三件套之一。v0.4 §4 明定：**Louis 親手寫，Claude Code 只能引用**。
   §11 建造順序第 1 步 —— 尚未完成，本檔目前刻意留空。

結構（§6.1）—— plan_vN.yaml 的七個區塊：
  meta                {case, sheet, version, based_on}   v1 的 based_on 填 null
  context             {kind, floor, scale, unit, orientation}  來自 02_sheets，中樞不得改
  judgments[]         {id, type, geometry, evidence[], confidence, note}
                      type 只能用 core/classes.py；evidence 至少一個
  overrides[]         {label, action, reason}            推翻視神經標籤必須留痕
  conflicts[]         {kind, detail, involved[]}         對不起來的寫這裡，不准抹平
  uncertain[]         {judgment, reason, basis}
  residual_handling[] {residual, action, detail}         v2 起必填；action ∈ {revise, report}

驗收六條（§6.2）在本檔定義「規則」，實際檢查邏輯寫在 planning/validate.py：
  1. schema 不合法／類別不在 classes.py
  2. 任一 judgment 的 evidence 為空，或引用的 id 不存在於 CSV
  3. geometry 座標無法追溯到 chain 或 measure 來源（禁止目測座標）
  4. overrides 缺 reason
  5. v2 起：上一輪任何殘差沒有出現在 residual_handling
  6. context 被改動

匯入本模組的程式會因為找不到符號而 ImportError —— 那是預期行為。
"""
