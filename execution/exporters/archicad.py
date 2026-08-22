"""ArchiCAD 匯出器 —— 預留接口，未實作

⚠ **上一版的 docstring 是錯的**：寫成「ArchiCAD 有官方 Python API（JSON 命令介面）」，
  讀起來像官方 API 就能建牆。**官方 API 建不了牆，這一點已經釘死了：**
  官方 JSON 介面（29.0.0.3000）共 74 條命令，全部 Create* 只有 CreateAttributeFolders /
  CreateLayout / CreateLayoutSubset / CreateViewMapFolder 四條，連 MoveElements /
  DeleteElements 都沒有；1.1MB 的官方 Python wrapper 文件裡 "Wall" 出現 0 次；
  反向測 API.CreateWalls 回 HTTP 404。

官方介面在本專案的角色只有兩個：提供 `API.ExecuteAddOnCommand` 這道橋，
以及 GetProductInfo / GetElementsByType 這些往返測試要用的**讀取**命令。

## 實際路徑：第三方 Tapir Add-On（硬相依，不是選配）

直接 HTTP POST JSON 到 Archicad 的本機埠，Python 端什麼都不用裝（40 行 urllib）：

    {"command": "API.ExecuteAddOnCommand",
     "parameters": {"addOnCommandId": {"commandNamespace": "TapirCommand",
                                       "commandName": "CreateWalls"},
                    "addOnCommandParameters": {"wallsData": [...]}}}
    → 回應在 result.addOnCommandResponse

需要：Archicad 25–29（建議 28/29）**正在執行且開著目標專案** ＋ 正式授權
（Demo 可連可測但不能存檔）＋ Tapir Add-On ≥ 1.5.7（MIT，十個預編譯檔）。
**沒有 token、沒有帳號、沒有 key** —— JSON/HTTP 介面官方原文
「it is embedded and always switched on in ARCHICAD」。

## available() 要做的事（不要等到 export 才炸）

埠**不是寫死的 19723，是範圍 19723–19743** —— 每個執行中的 Archicad 各佔一個。
同時開兩份專案時 19723 未必是你要的那份，**牆會安靜地建進錯的檔案**。所以：
掃描埠 → `API.GetProductInfo`（無參數、無副作用）確認版本 →
`API.IsAddOnCommandAvailable`（TapirCommand / CreateWalls）確認 Tapir 有裝 →
`GetProjectInfo` 印出目標專案名要求人確認。任一失敗回 (False, 原因)。

## 實作時最會悄悄出錯的四件事

1. **必須明寫 `'referenceLineLocation': 'Center'`。** 不寫就沿用專案 Wall 工具的
   預設，很多範本是 Outside → 每道牆整體平移半個牆厚，**畫面上看起來完全正常、
   不報錯，只有量測時才發現**。
2. 單位一律**公尺與弧度**（plan 是 cm，全部 ÷100）。GetCalculationUnits 只影響畫面
   顯示，不改變 API 收發的數值。
3. 有給 floorIndex 時，zCoordinate 被解讀成「相對該樓層的 bottomOffset」；沒給才是絕對 Z。
4. 回傳型別是 ElementIdsOrErrors —— **陣列裡可以逐項夾帶 error**。1979 掃描圖必有
   退化／零長軸線，`walls['elements'][i]['elementId']` 對被拒絕的牆會直接 KeyError。
   逐項檢查 'error' 是必須的，不是防禦性加分。

互動除錯可用 SzamosiMate/tapir-archicad-MCP，但 export() 不經過它（見 base.py）。
"""

from execution.exporters.base import Exporter

PORT_RANGE = range(19723, 19744)   # 每個執行中的 Archicad 各佔一個，必須掃描
TAPIR_NAMESPACE = "TapirCommand"


class ArchiCad(Exporter):
    name = "archicad"
    ext = ""
    needs = "live_app"
    native_objects = True
    needs_addon = "Tapir Add-On ≥ 1.5.7（MIT，第三方，硬相依）"
    notes = "官方 JSON API 建不了牆，只是橋與讀取通道；牆靠 Tapir 的 CreateWalls"
