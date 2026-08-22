"""execution/exporters/registry.py —— 選匯出器

用法：
    from execution.exporters.registry import get_exporter
    ex = get_exporter()          # 預設 dxf（§12：MVP 輸出 DXF 優先）
    ex = get_exporter("rhino")

新增目標軟體＝寫一支 Exporter 子類、在 EXPORTERS 加一列。s07_execute 不動。
"""

from execution.exporters.archicad import ArchiCad
from execution.exporters.dxf import Dxf
from execution.exporters.ifc import Ifc
from execution.exporters.revit import Revit
from execution.exporters.rhino import Rhino
from execution.exporters.visualarq import VisualArq

EXPORTERS = {c.name: c for c in (Dxf, Rhino, VisualArq, ArchiCad, Revit, Ifc)}
DEFAULT = "dxf"


def get_exporter(name: str = DEFAULT):
    if name not in EXPORTERS:
        raise KeyError(f"未知的匯出器 {name!r}；可用：{sorted(EXPORTERS)}")
    ex = EXPORTERS[name]()
    if ex.gated:
        raise PermissionError(f"匯出器 {name!r} 目前被規格擋下：{ex.gate_reason}")
    return ex


def table() -> list:
    """[{name, ext, needs, gated}] —— 給人看現在有哪些路、各需要什麼。"""
    return [{"name": c.name, "ext": c.ext, "needs": c.needs, "gated": c.gated}
            for c in EXPORTERS.values()]
