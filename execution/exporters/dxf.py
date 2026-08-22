"""DXF 匯出器 —— MVP 的唯一輸出（規格 §8、§12：MVP 輸出 DXF 優先）

ezdxf，純檔案輸出。**AutoCAD 這條路就是 DXF** —— 不需要另寫 AutoCAD 匯出器，
不需要 Autodesk 授權或憑證，也不需要做 DWG（ODA 轉檔買不到任何原生性，
只是同一批線段換個容器）。

★ `native_objects = False` 不是妥協，是天花板：**純 AutoCAD 根本沒有牆物件**。
  智慧牆 AecDbWall 只存在於 AutoCAD Architecture，且在 DXF/DWG 裡是 proxy object，
  沒有 Object Enabler 就讀不懂（ezdxf 直接把 AEC 實體當無法解析的 proxy 跳過）。
  要「真的牆」請走 ifc / archicad / revit / visualarq。

閘門：DXF 在 ArchiCAD 打得開（§11 第 5 步）。
"""

from execution.exporters.base import Exporter


class Dxf(Exporter):
    name = "dxf"
    ext = ".dxf"
    needs = "file"
    native_objects = False
    notes = "線段／polyline／hatch。AutoCAD 沒有牆物件，這是天花板不是取捨。"

    def export(self, plan, out_dir) -> list:
        raise NotImplementedError("DXF 匯出未實作（§11 第 5 步）")
