"""core/classes.py —— 15 類偵測類別

★ 契約三件套之一。v0.4 §4 明定：**Louis 親手寫，Claude Code 只能引用**。
   §11 建造順序第 1 步 —— 尚未完成，本檔目前刻意留空。

鐵則：**順序即 id，永不重排。** 新類別只能往後加，不能插隊、不能刪。

用途：
  - 03_detections / 03_elements 的類別欄
  - plan_vN.yaml 的 judgments[].type 只能用這裡的類別（§6.1）
  - validate 退件規則 1：類別不在本檔即退（§6.2）

匯入本模組的程式會因為找不到符號而 ImportError —— 那是預期行為。
"""
