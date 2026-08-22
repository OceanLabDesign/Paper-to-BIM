"""Rhino 匯出器 —— 預留接口，未實作

rhino3dm 純檔案輸出，**不需要 Rhino 執行、不需要憑證**。
本機另有 rhinomcp 可在 Rhino 內執行 RhinoCommon，那是 live_app 路線，
與這支互補：這支給不開 Rhino 的人，那條給要即時操作的人。
"""

from execution.exporters.base import Exporter


class Rhino(Exporter):
    name = "rhino"
    ext = ".3dm"
    needs = "file"
    gated = False
    gate_reason = ""
