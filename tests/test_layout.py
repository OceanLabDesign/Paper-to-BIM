"""tests/test_layout.py —— L1 圖幅 mapping 的確定性部分

`python3 tests/test_layout.py`

只測不需要 VLM 的那半：樓層解析、分組、網格位置推定。
判讀那半（讀標題欄）由多模態模型做，不在這裡測 —— 它的驗收在真實案件上。
"""

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.dont_write_bytecode = True

from perception.s02_layout import parse_floor, group_tiles, assign_cells  # noqa: E402

# 全部取自 cases/79-B37001_七賢二路 標題欄上的實際寫法
FLOORS = [
    ("地下室一樓", (-1, -1)), ("一樓", (1, 1)), ("二樓", (2, 2)), ("三樓", (3, 3)),
    ("四樓～十樓", (4, 10)), ("四樓~十樓", (4, 10)), ("十一樓", (11, 11)),
    ("十二樓", (12, 12)), ("地下二樓", (-2, -2)), ("二十樓", (20, 20)),
    ("屋頂", (None, None)), ("", (None, None)), ("看不清", (None, None)),
]

def tile(i, name="", part="無", tb=False):
    return {"tile_id": f"p{i:02d}", "has_title_block": tb, "part": part,
            "drawing_name": name, "drawing_no": "", "floor": "", "scale": ""}

def main() -> int:
    bad = []

    for text, want in FLOORS:
        got = parse_floor(text)
        if got != want:
            bad.append(f"parse_floor({text!r}) = {got}，應為 {want}")
    print(f"[1] 樓層解析：{len(FLOORS)} 例{'全對' if not bad else ' 有錯'}")

    # 分組：N 不固定 —— 這組是 4、3、5 片
    readings = ([tile(1, "一樓平面圖", "圖名區", True), tile(2), tile(3),
                 tile(4, part="簽核區", tb=True)]
                + [tile(5, "二樓平面圖", "圖名區", True), tile(6), tile(7)]
                + [tile(8, "三樓平面圖", "圖名區", True), tile(9), tile(10),
                   tile(11), tile(12)])
    groups, orphans = group_tiles(readings)
    sizes = [len(g["tiles"]) for g in groups]
    if sizes != [4, 3, 5]:
        bad.append(f"分組大小 {sizes}，應為 [4, 3, 5]（N 不固定，不可寫死 4）")
    if orphans:
        bad.append(f"不該有 orphans，卻有 {[o['tile_id'] for o in orphans]}")
    print(f"[2] 分組（N 不固定）：{sizes}")

    # 錨點之前的片 → orphans，不硬塞
    g2, orph2 = group_tiles([tile(1), tile(2, "圖A", "圖名區", True), tile(3)])
    if [o["tile_id"] for o in orph2] != ["p01"]:
        bad.append(f"錨點前的片應進 orphans，實際 {[o['tile_id'] for o in orph2]}")
    print(f"[3] 錨點前的片：{[o['tile_id'] for o in orph2]} 進 orphans（不猜歸屬）")

    # 網格：底列由標題欄定，其餘標 ambiguous
    cells, rows, cols = assign_cells(groups[0])
    bottom = {c["tile_id"]: (c["row"], c["col"]) for c in cells if c["status"] == "assigned"}
    amb = [c["tile_id"] for c in cells if c["status"] == "ambiguous"]
    if (rows, cols) != (2, 2):
        bad.append(f"4 片 2 個標題欄 → 應推得 2×2，實際 {rows}×{cols}")
    if bottom.get("p04") != (1, 0) or bottom.get("p01") != (1, 1):
        bad.append(f"底列應為 簽核區(1,0)、圖名區(1,1)，實際 {bottom}")
    if sorted(amb) != ["p02", "p03"]:
        bad.append(f"非底列的片應標 ambiguous，實際 {amb}")
    print(f"[4] 網格 {rows}×{cols}：底列 {bottom}｜待定 {amb}")

    if bad:
        print("\n✗ 有問題：")
        for b in bad:
            print("  -", b)
        return 1
    print("\n✓ L1 確定性部分全數通過")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
