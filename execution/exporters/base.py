"""execution/exporters/base.py —— 匯出器介面

s07_execute 只認這個介面。**每個匯出器都只讀 plan，不讀任何 03/04 檔**
（§8 腦手分離鐵則）—— 加新匯出器不會鬆動這條。

## 為什麼不只有 access 一個欄位

決定一條路能不能用的，不只是「怎麼進去」，還有三件事：
能不能產出**原生參數化物件**（真的牆，不是線段）、有沒有**沒被記錄的硬相依**
（第三方外掛、作業系統）、以及**產出物是不是檔案**。所以類屬性有五個。

## MCP 不得成為任何 Exporter 的相依

Archicad、Revit、Rhino 三家都有 MCP server，但它們**只掛開發者的 MCP config，
不進這裡**。MCP 是給模型在不知道 schema 時臨場探索用的；我們相反 ——
schema 已知、固定、可以寫死。經過 MCP 等於在確定性管線裡插一個非確定性元件，
直接牴觸 §8「不准有 LLM、同一份 plan 跑兩次要得到同一份輸出」。
互動除錯請用對應的 MCP server，但 `export()` 不經過它。

## 確定性的定義（§8）

**不是 byte-identical。** IFC 每次產生新的 GlobalId、rhino3dm 每次寫新的物件 GUID、
IFC header 還帶時間戳 —— 照字面讀，兩條純檔案路線都一定過不了。
實際要求是：
  - **幾何與屬性等價**；比對時排除 GUID 與時間戳
  - id 盡量從 judgment id **決定性導出**（IFC 可用
    `ifcopenshell.guid.compress(uuid5(NS, judgment_id).hex)`），讓兩次產出可逐筆對照
"""

NEEDS = ("file", "live_app", "cloud_token")
# 刻意不放 "mcp" —— 免得有人以為那是可選項。理由見上面。


class Exporter:
    name = "base"
    ext = ""
    needs = "file"

    native_objects = False  # 能否產出原生參數化物件（真的牆），而不只是幾何
    needs_addon = ""        # 沒被 needs 表達出來的硬相依（第三方外掛與最低版本）
    os_required = ""        # "windows" 等；空字串＝不限
    notes = ""              # 一句話講這條路的天花板或關鍵前提

    gated = False           # True 代表 §12 明令現在不准做
    gate_reason = ""

    def export(self, plan: dict, out_dir) -> list:
        """把 plan 落地，回傳產出的檔案路徑 list。

        紀律（§8、裁決 §6）：
          - **只讀 plan**，不讀 03/04
          - 確定性見上面的定義（等價，不是 byte-identical）
          - plan 裡由 core.config.ASSUMED 導出的值（thickness_src == "assumed"）
            → 檔名帶 core.config.DRAFT_SUFFIX

        ⚠ needs == "live_app" 的匯出器沒有檔案產出（東西建在執行中的專案裡）。
          待決：那三支改回傳「建立報告」JSON 的路徑（每筆 judgment id → 建出的
          元素 id／錯誤／警告），確定性落在報告內容上。**這是介面層的裁決，
          不該由匯出器自己決定** —— 見 待決事項.md。
        """
        raise NotImplementedError(f"{type(self).__name__}.export 未實作")

    def available(self) -> tuple:
        """回傳 (可用嗎, 說明)。給 registry 在選之前先問，不要等到 export 才炸。

        live_app 的匯出器應該在這裡做完連線探測與外掛檢查 —— 那些失敗都是
        「環境沒準備好」，不是程式錯誤，要給人看得懂的話。
        """
        return (False, f"{self.name} 尚未實作")
