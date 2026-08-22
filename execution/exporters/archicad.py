"""ArchiCad 匯出器 —— 預留接口，未實作

ArchiCAD 有官方 Python API（JSON 命令介面），對**執行中的 ArchiCAD** 下指令。
不需要 token。§11 第 8 步的「ArchiCAD 四道牆往返測試」就是驗這條路。
"""

from execution.exporters.base import Exporter


class ArchiCad(Exporter):
    name = "archicad"
    ext = ""
    needs = "live_app"
    gated = False
    gate_reason = ""
