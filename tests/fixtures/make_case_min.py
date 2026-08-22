"""tests/fixtures/make_case_min.py —— 造出 §13 自測要的最小案件

`python3 tests/fixtures/make_case_min.py` → 產生 tests/fixtures/case_min/

為什麼要這個：§13 派工單要 planning/validate.py「附一個用 68 年案 plan_v1 樣本的自測」，
但真實 CSV 要等 §11 第 2–5 步跑出來。沒有測資，validate 只驗得到「該退的會不會退」，
驗不到「該過的會不會過」—— 而後者才是驗收閘門的重點。

這份測資刻意小到能一眼看完，而且**就是 §11 第 4 步的第一筆迴歸測試**：
68 年案的 403 + 403 = 806。一道 806cm 的牆，尺寸鏈由兩個 403 讀數組成且閉合。

所有欄位標題**一律從 core.fields 取**，不在這裡重打 —— 契約改了重跑本腳本即可，
不會出現測資與契約各說各話。
"""

import csv
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from core import case, fields                                    # noqa: E402

OUT = Path(__file__).resolve().parent / "case_min"

# 每個 CSV 一份資料列。鍵＝欄位名，缺的欄位留空。
# id 命名對得上 core.fields.EVIDENCE_NS 的前綴：det#d001、chain#c001、read#r001…
ROWS = {
    "sheets": [dict(sheet_id="A-2_1F", page=1, kind="plan", floor="1F",
                    scale=100, unit="cm", orientation=0,
                    frame_wkt="POLYGON((0 0,1200 0,1200 900,0 900,0 0))",
                    title_block_wkt="POLYGON((900 0,1200 0,1200 150,900 150,900 0))",
                    version_hint="", note="最小測資")],
    "exclude": [dict(exclude_id="e01", sheet_id="A-2_1F", kind="title_block",
                     bbox_wkt="POLYGON((900 0,1200 0,1200 150,900 150,900 0))",
                     note="標題欄")],
    "quality": [dict(quality_id="q01", sheet_id="A-2_1F", block_x=0, block_y=0,
                     block_px=256, contrast=0.82, noise=0.05, stroke_density=0.11,
                     level="good")],
    # 一對平行線 → 牆。間距 28px ≈ 24cm（core.config：24cm × 1.181 ≈ 28px）
    "lines": [
        dict(line_id="l001", sheet_id="A-2_1F", tile_id="p01_t01",
             wkt="LINESTRING(0 0, 952 0)", length_px=952, angle_deg=0,
             thickness_px=2, quality_zone="good"),
        dict(line_id="l002", sheet_id="A-2_1F", tile_id="p01_t01",
             wkt="LINESTRING(0 28, 952 28)", length_px=952, angle_deg=0,
             thickness_px=2, quality_zone="good"),
    ],
    "texts": [
        dict(text_id="t001", sheet_id="A-2_1F", tile_id="p01_t01", text="403",
             bbox_wkt="POLYGON((200 -40,260 -40,260 -10,200 -10,200 -40))",
             angle_deg=0, conf=0.97, region="body"),
        dict(text_id="t002", sheet_id="A-2_1F", tile_id="p01_t01", text="403",
             bbox_wkt="POLYGON((680 -40,740 -40,740 -10,680 -10,680 -40))",
             angle_deg=0, conf=0.96, region="body"),
    ],
    "detections": [dict(det_id="d001", sheet_id="A-2_1F", class_name="wall",
                        bbox_wkt="POLYGON((0 0,952 0,952 28,0 28,0 0))",
                        detector="rule_v1", conf=0.91,
                        evidence="line#l001|line#l002", provenance="rule_v1",
                        quality_zone="good", status="proposed")],
    "elements": [dict(element_id="x001", sheet_id="A-2_1F", class_name="wall",
                      geom_wkt="LINESTRING(0 14, 952 14)", thickness_cm=24,
                      thickness_src="measured", source_lines="l001|l002",
                      conf=0.91, evidence="det#d001", provenance="rule_v1",
                      quality_zone="good", status="proposed")],
    # 三源一致 → green。§1.2：src_geom 完全不看文字，走端點距離 × 比例尺
    "readings": [
        dict(id="r001", sheet_id="A-2_1F", kind="dim", value=403, unit="cm",
             conf=0.98, status="green", src_paddle=403, src_vlm=403, src_geom=403,
             bbox_x=200, bbox_y=-40, bbox_w=60, bbox_h=30, crop="04_crops/r001.png",
             verified_value="", verified_by="", verified_at="", note=""),
        dict(id="r002", sheet_id="A-2_1F", kind="dim", value=403, unit="cm",
             conf=0.98, status="green", src_paddle=403, src_vlm=403, src_geom=403,
             bbox_x=680, bbox_y=-40, bbox_w=60, bbox_h=30, crop="04_crops/r002.png",
             verified_value="", verified_by="", verified_at="", note=""),
    ],
    # ★ 403 + 403 = 806，閉合（§11 第 4 步的第一筆迴歸測試）
    "chains": [dict(chain_id="c001", sheet_id="A-2_1F", axis="X",
                    wkt="LINESTRING(0 -30, 806 -30)", sum_value=806, total_value=806,
                    delta=0, closed=1, unit="cm")],
    "chain_members": [dict(chain_id="c001", seq=1, reading_id="r001", value=403),
                      dict(chain_id="c001", seq=2, reading_id="r002", value=403)],
}


def build() -> Path:
    case.ensure_case(OUT)
    for key, rows in ROWS.items():
        cols = fields.BY_FILE[key]
        with case.path(OUT, key).open("w", newline="", encoding="utf-8") as f:
            w = csv.DictWriter(f, fieldnames=cols)
            w.writeheader()
            for r in rows:
                unknown = set(r) - set(cols)
                if unknown:
                    raise KeyError(f"{key}: 欄位 {sorted(unknown)} 不在 core.fields.{key.upper()}")
                w.writerow({c: r.get(c, "") for c in cols})
    return OUT


if __name__ == "__main__":
    p = build()
    print(f"✓ 已產生 {p.relative_to(ROOT)}")
    for f in sorted(p.glob("*.csv")):
        print(f"  {f.name:24} {sum(1 for _ in f.open(encoding='utf-8')) - 1} 列")
