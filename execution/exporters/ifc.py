"""Ifc 匯出器 —— 預留接口，未實作

IfcOpenShell 純檔案輸出，參數化寫法（v0.3 規格）。
**規格明令現在不要寫** —— gated=True，registry 會擋。
"""

from execution.exporters.base import Exporter


class Ifc(Exporter):
    name = "ifc"
    ext = ".ifc"
    needs = "file"
    gated = True
    gate_reason = "§12：等 ArchiCAD 四道牆往返測試通過才實作（§11 第 8 步）"
