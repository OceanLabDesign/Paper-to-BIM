"""Rhino 匯出器 —— 預留接口，未實作

rhino3dm 純 Python 離線寫 .3dm：**不需要 Rhino 執行、不需要授權、不需要 token**
（wheel 完全自含，Win / macOS / Linux 都有）。

★ `native_objects = False` 是查證過的事實，不是保守估計：**Rhino 沒有
  wall / door / window 型別**（rhino3dm 全部 213 個公開型別裡沒有），
  Rhino 9 的新功能清單也沒有任何 BIM 元件。天花板是 `IsSolid=True` 的 Extrusion。
  要「真的牆」在 Rhino 裡，那是 VisualARQ 的事（見 visualarq.py）。

相對於 DXF 的加值（這才是這支存在的理由）：
  - **封閉實體**（可算體積、可布林），DXF 給不了
  - **per-object UserString** —— 把 judgment_id / evidence / thickness_src
    帶到下游，證據鏈不斷在匯出這一步

## 與 rhinomcp 的關係

本機有一份 OceanLab fork（../rhinomcp，37 支工具，需 Rhino 8 ＋ 外掛 ＋
在 Rhino 裡執行 `mcpstart`）。**但它不該當落地路徑**：兩條路的產物上限完全一樣
（Rhino 本體就是沒有牆型別），MCP 那條卻多了 Rhino 要開著、逾時、以及
「其實做完了但看起來失敗」的重複風險，還在確定性管線裡插了非確定性元件（§8）。
rhinomcp 的定位是**看與改**（capture_viewport / diagnose_edge_pair），不是第二套實作。

## 實作要點

牆 → Extrusion（SetPathAndUp + SetOuterProfile，profile 畫在世界 XY 平面），柱同一套。
門窗先只做「在牆上開洞 ＋ 一個 block 佔位」。其餘類別走 UserString 或 TextDot。
文件單位務必顯式設 Centimeters ＋ ModelAbsoluteTolerance 0.01。
物件 GUID 每次寫都會變 —— 確定性比對要排除它（見 base.py）。
"""

from execution.exporters.base import Exporter


class Rhino(Exporter):
    name = "rhino"
    ext = ".3dm"
    needs = "file"
    native_objects = False
    notes = ("Rhino 沒有牆型別，天花板是 Extrusion；"
             "加值在封閉實體與 per-object UserString，不在原生 BIM")
