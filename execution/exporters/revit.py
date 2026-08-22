"""Revit 匯出器 —— 預留接口，未實作

## 本機路線：pyRevit Routes（不需要任何 token）

exporter 端 POST `http://127.0.0.1:48884/paper2bim/plan/`；Revit 端 handler 用
Level.Create → WallType.Duplicate + SetCompoundStructure → Wall.Create →
NewOpening / NewFamilyInstance，整批包一個 Transaction。

需要（三個前提缺一不可）：
  1. **Windows** —— Revit 沒有 Mac 版
  2. **Revit 完整版** 2019–2027 並登入授權。★ **Revit LT 沒有 API**，
     pyRevit / Dynamo / add-in 全都不能用，整條路直接不成立
  3. pyRevit ≥ 6.5.4（GPL-3.0）

★ **不需要 client_id / client_secret。** Revit 要 Autodesk 帳號登入那是**產品授權**，
  不是 API token；pyRevit routes 的 HttpRequestHandler 完全沒有任何 auth / token 檢查。
⚠ 但「沒有認證」有代價：pyRevit 的 routes host 預設是空字串＝綁 0.0.0.0，
  **同網段任何人都能 POST 改你的模型**。必須在 pyRevit Settings → Routes 設成 127.0.0.1。
  探活 URL 是 `/routes/status`（無尾斜線）。

Dynamo 刻意不列為主線：它的 Python 節點要用 TransactionManager.Instance
.EnsureInTransaction(doc)，不能照抄 pyRevit 的 `using (Transaction t = …)`，
而且 Dynamo Core 3→4 換過 Python 引擎，跨版本維護成本比 pyRevit 高。

## 實作時的三個硬事實

1. **厚度不是牆的參數，是 WallType 的參數。** 先把 plan 裡所有 thickness 去重，
   每種厚度做一次 `WallType.Duplicate` → `GetCompoundStructure()`（**回傳的是副本**）
   → `SetLayerWidth` → **`SetCompoundStructure()` 寫回去**（最常見的錯就是改了副本
   忘記寫回），快取 `{thickness_cm: ElementId}`，不要每道牆 Duplicate 一次。
2. 單位是**十進位英尺**。一律走
   `UnitUtils.ConvertToInternalUnits(值, UnitTypeId.Centimeters)`
   （2021 前是 DisplayUnitType.DUT_CENTIMETERS，網路上舊範例大量用已淘汰寫法）。
3. FamilySymbol 用之前必須 `if not symbol.IsActive: symbol.Activate(); doc.Regenerate()`
   —— 漏掉**不會報錯，但牆上的洞不會生成**。

handler 簽章要寫 `def build(uiapp, request)` 再取 `plan = request.data`：
POST body **不會**以參數名注入，寫成 `def build(uiapp, plan)` 時
**不會噴 TypeError，plan 會靜靜地等於 None**。

## 雲端路線：APS Design Automation for Revit —— 不實作

**這是整份盤查裡唯一真的需要 API 憑證的一條**：APS App 的 client_id + client_secret
（2-legged OAuth）＋ Flex token 付費 ＋ 自寫的 C# AppBundle ＋ .rte 範本。
本機不需安裝 Revit，但沒有 Revit 也無法驗收產出。
限制：不能引用 RevitAPIUI.dll、不能用 WinForms/WPF、沒有 ActiveDocument/ActiveView。
介面留著（見 registry 的 needs='cloud_token' 一格），等真要對外做服務再說。

互動除錯可用 Demolinator/revit-mcp-server（走同一個 pyRevit Routes 底座），
但 export() 不經過它（見 base.py）。
"""

from execution.exporters.base import Exporter

ROUTES_URL = "http://127.0.0.1:48884/paper2bim/plan/"
STATUS_URL = "http://127.0.0.1:48884/routes/status"   # 無尾斜線


class Revit(Exporter):
    name = "revit"
    ext = ""
    needs = "live_app"
    native_objects = True
    needs_addon = "pyRevit ≥ 6.5.4；Revit 完整版（LT 沒有 API，整條路不成立）"
    os_required = "windows"
    notes = "本機 pyRevit Routes 不需 token，但預設綁 0.0.0.0 零認證，務必改 127.0.0.1"
