"""Revit 匯出器 —— 預留接口，未實作

本機路線：Revit API（pyRevit／Dynamo）在**執行中的 Revit** 裡跑，不需要 token。
雲端路線：Autodesk Platform Services 需要憑證 —— **那是這批工具裡唯一真的要 token 的**，
取得前這支維持未實作，介面已備妥。
"""

from execution.exporters.base import Exporter


class Revit(Exporter):
    name = "revit"
    ext = ""
    needs = "live_app"
    gated = False
    gate_reason = ""
