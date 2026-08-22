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

import re

from execution.exporters.base import Exporter

LAYER = "PB_WALL"


def _endpoints(wkt):
    return [(float(x), float(y))
            for x, y in re.findall(r"(-?\d+(?:\.\d+)?) (-?\d+(?:\.\d+)?)", wkt)]


class Dxf(Exporter):
    name = "dxf"
    ext = ".dxf"
    needs = "file"
    native_objects = False
    notes = "線段／polyline／hatch。AutoCAD 沒有牆物件，這是天花板不是取捨。"

    def export(self, plan, out_dir) -> list:
        """plan → out/*.dxf。單位公分，牆心線畫成 LINE。

        ⚠ 只讀 plan。任何一筆 judgment 的幾何若無法從 plan 本身取得，
        **不要回頭去讀 03/04 補** —— 那是中樞沒說清楚，該退件不是該補救。
        """
        import ezdxf
        from core.config import ASSUMED_SRC, DRAFT_SUFFIX

        doc = ezdxf.new("R2010", setup=True)
        doc.header["$INSUNITS"] = 5                     # 5 = 公分
        msp = doc.modelspace()
        doc.layers.add(LAYER, color=1)

        drafty = False
        for j in plan.get("judgments", []):
            geom = j.get("geometry", {})
            wkt = geom.get("axis_wkt")
            if not wkt:
                continue
            pts = _endpoints(wkt)
            if len(pts) < 2:
                continue
            msp.add_line(pts[0], pts[-1],
                         dxfattribs={"layer": LAYER,
                                     "thickness": 0})
            if geom.get("thickness_src") == ASSUMED_SRC:
                drafty = True

        meta = plan.get("meta", {})
        stem = f"{meta.get('sheet') or 'sheet'}_v{meta.get('version', 1)}"
        if drafty:
            stem += DRAFT_SUFFIX
        path = out_dir / f"{stem}{self.ext}"
        doc.saveas(path)
        return [path]
