"""VisualArq 匯出器 —— 預留接口，未實作

VisualARQ 是 Rhino 外掛，牆／門／窗是它的參數化物件，
必須在**執行中的 Rhino**裡透過 RhinoCommon／rhinoscriptsyntax 建立。
不需要 token，需要 Rhino 與 VisualARQ 的授權與安裝。
相對於 rhino.py 的價值：出來的是真的牆，不是線段。
"""

from execution.exporters.base import Exporter


class VisualArq(Exporter):
    name = "visualarq"
    ext = ".3dm"
    needs = "live_app"
    gated = False
    gate_reason = ""
