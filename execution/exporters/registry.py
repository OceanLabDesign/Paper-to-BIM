"""execution/exporters/registry.py —— 選匯出器

用法：
    from execution.exporters.registry import get_exporter, table
    ex = get_exporter()          # 預設 dxf（§12：MVP 輸出 DXF 優先）
    print(table())               # 現在有哪些路、各需要什麼、能不能產原生物件

新增目標軟體＝寫一支 Exporter 子類、在 EXPORTERS 加一列。s07_execute 不動。

**MCP server 不在這裡**（見 base.py）：Archicad / Revit / Rhino 三家都有，
但只掛開發者的 MCP config 當互動除錯用，不得成為 exporter 的相依。
"""

from execution.exporters.archicad import ArchiCad
from execution.exporters.dxf import Dxf
from execution.exporters.ifc import Ifc
from execution.exporters.revit import Revit
from execution.exporters.rhino import Rhino
from execution.exporters.visualarq import VisualArq

# 順序即建議的實作優先序（見 待決事項.md 的盤查結論）
EXPORTERS = {c.name: c for c in (Dxf, Ifc, ArchiCad, Rhino, Revit, VisualArq)}
DEFAULT = "dxf"


def get_exporter(name: str = DEFAULT):
    if name not in EXPORTERS:
        raise KeyError(f"未知的匯出器 {name!r}；可用：{sorted(EXPORTERS)}")
    ex = EXPORTERS[name]()
    if ex.gated:
        raise PermissionError(f"匯出器 {name!r} 目前被規格擋下：{ex.gate_reason}")
    return ex


def table() -> list:
    """給人看的一覽。priority 即 EXPORTERS 的順序。

    `native_objects` 這欄是重點 —— 沒有它，dxf/rhino 會跟 archicad/revit 混在一起，
    而使用者真正在問的是「哪條路給我真的牆」。
    """
    return [{"priority": i,
             "name": c.name,
             "ext": c.ext,
             "needs": c.needs,
             "native": c.native_objects,
             "token": c.needs == "cloud_token",
             "addon": c.needs_addon,
             "os": c.os_required,
             "gated": c.gated,
             "notes": c.notes}
            for i, c in enumerate(EXPORTERS.values(), 1)]
