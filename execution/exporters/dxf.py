"""DXF 匯出器 —— MVP 的唯一輸出（規格 §8、§12：MVP 輸出 DXF 優先）

ezdxf，純檔案輸出。**AutoCAD 這條路就是 DXF** —— 不需要另寫 AutoCAD 匯出器，
也不需要 Autodesk 的任何憑證。
閘門：DXF 在 ArchiCAD 打得開（§11 第 5 步）。
"""

from execution.exporters.base import Exporter


class Dxf(Exporter):
    name = "dxf"
    ext = ".dxf"
    needs = "file"

    def export(self, plan, out_dir) -> list:
        raise NotImplementedError("DXF 匯出未實作（§11 第 5 步）")
