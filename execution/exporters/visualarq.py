"""VisualARQ 匯出器 —— 預留接口，未實作。**本機（macOS）0% 可執行**

⚠ **上一版的 docstring 是錯的**：寫成「透過 RhinoCommon／rhinoscriptsyntax 建立」。
  **rhinoscriptsyntax 建不出 VisualARQ 牆。** 要用獨立的 .NET 組件 VisualARQ.Script：

      clr.AddReference('VisualARQ.Script')
      from VisualARQ import Script as va          # 不是 import VisualARQ.Script as va

## 為什麼 needs 是 file 而不是 live_app

export() **不連 Rhino**，而是產生一支 `.py` 腳本檔，由使用者在 Windows 端的 Rhino 用
`_-ScriptEditor _R "path"` 執行。這樣 exporter 本身可以在 macOS 上開發、單元測試、
比對兩次產出的 .py 是否等價 —— **把 live_app 依賴推到最後一公尺，這是唯一能讓這條
符合 §8 確定性要求的接縫形狀。**

## 執行端的門檻（這條路的真正代價）

  - **Windows only。** 官方系統需求逐字「It only works on Windows.」，
    是 C++ 外掛的架構限制（要等 Rhino for Mac 支援 C++ 外掛），
    Asuni 已明說沒有計畫。**這台是 macOS。**
  - Rhino 8 SR11+ 或 Rhino 7 SR34+
  - **VisualARQ 3 商業授權**（約 US$755 起）。90 天試用到期後
    **連「儲存 VisualARQ 物件」都會被停用** —— 不是功能少一點，是整條路死掉。
  - 不需要 token（VisualARQ.Script.dll 是裝在 Rhino 旁邊的本機 .NET 組件，
    不是網路服務）。

## 只用有官方背書的函式

有 Asuni 官方人員貼過可運行程式碼的只有這幾個：
    va.GetCurrentWallStyle()
    va.AddWall(styleId, Point3d, Point3d)
    AddBuilding(name, elevation) → AddLevel(buildingId, name, elevation)
        （**必須先有 building 才掛得上 level**；官方 API 真的有 `GetLevelBuidlingId`
          這個拼字錯誤，照抄別修）
    AddWindowStyle(name, profileTemplateId) / AddWindow(styleId, Point3d, angle)
        （profile 曲線必須 ChangeDimension(2)，否則爆保護記憶體錯誤）

★ AddWallStyle / AddWallLayer / AddWallsFromCurves / SetWallAlignment 這一整串
  只出現在某個一天建完即棄的第三方 repo，**沒有官方背書，不要當成存在**。

## 為什麼不走 rhinomcp 的 C# 執行器

`plugin/Functions/ExecuteRhinoCommonCSharp.cs` 的 Roslyn ScriptOptions 是**寫死的
參考清單**（mscorlib / System.Linq / List / RhinoCommon / System.Runtime），
**VisualARQ 的組件不在裡面**，所以 execute_rhinocommon_csharp_code 現況呼叫不到它。
繞法有三條（Python 執行器可 clr.AddReference / Grasshopper 元件 / 改 fork 加參考），
但都需要 Rhino 執行中 —— 而產腳本這條連 Rhino 都不用開就能做完九成，所以選它。
"""

import sys

from execution.exporters.base import Exporter


class VisualArq(Exporter):
    name = "visualarq"
    ext = ".py"                  # 產出的是腳本，不是模型檔
    needs = "file"
    native_objects = True
    needs_addon = "VisualARQ 3 商業授權（試用到期後連存檔都停用）＋ Rhino 8 SR11+"
    os_required = "windows"
    notes = "export() 產一支 .py 由使用者在 Windows 的 Rhino 執行；不連線"

    def available(self) -> tuple:
        if sys.platform != "win32":
            return (False, f"VisualARQ 是 Windows-only，本機是 {sys.platform}；"
                           "產腳本可以，但沒有 Windows + Rhino + VisualARQ 授權就驗不到")
        return (False, "visualarq 尚未實作")
