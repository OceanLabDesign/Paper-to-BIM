"""core/fields.py —— 各 CSV 欄位清單

★ 契約三件套之一。規格 §4 原規定是「專案負責人親手寫，程式只能引用」——
  本檔由 Claude Code 依負責人指派代擬。**尚未定版，需負責人逐項確認。**

標記說明：
  【定版】= 規格或《待決事項—裁決》已逐字寫死，照抄，不要改
  【草案】= 規格只描述了「這個檔要放什麼」，欄位名由本檔代擬，等負責人點頭

原則（v0.3 沿用）：
  - CSV 為主，**幾何一律用 WKT 欄位**（`*_wkt`）
  - 編號即順序；id 欄一律叫 `*_id`，值不含命名空間前綴
  - 讀值一律走 core.io.final()：`verified_value` 優先於 `value`（§1.1）
  - 不確定往上傳不往下傳：值未定就留空，不要填 0 或猜測值
"""

# ─────────────────────────────────────────────────────────────
# 01 拆片
# ─────────────────────────────────────────────────────────────
# 【定版】裁決 §1 / 規格 §3.1
# s01 產出時 rotation、upright_file 留空，由 s01b 回填；
# s01b 填 rotation 時必須同步重算 x/y（轉正會改變片在頁座標系的位置）。
OFFSETS = ("tile_id", "page", "x", "y", "w", "h", "rotation", "upright_file")

# ─────────────────────────────────────────────────────────────
# 02 版面
# ─────────────────────────────────────────────────────────────
# 【草案】規格 §8：圖種/樓層/比例/單位/方向/圖框範圍/標題欄/版本線索
# orientation 抄自 OFFSETS.rotation（裁決 §1），是紀錄不是重新判斷。
# 前五欄（kind…orientation）是 plan 的 context 來源，中樞不得更改（§6.1、§6.2 規則 6）。
# ★ 2026-08-22 修正：原本有 `page` 欄，隱含「一頁＝一張圖」。實測不成立 ——
# 原圖是 A1／A2，事務所影印機最多 A3，**一張圖被拆成 N 張 A3**（N 不固定）。
# 片與圖的歸屬改由 SHEET_TILES 這張 join table 表達（見 ADR 0009）。
# 樓層存**範圍**：drawing_floor 保留圖上原樣的寫法（「四樓～十樓」），
# floor_from / floor_to 是正規化整數（地下一樓 = -1，一樓 = 1），供程式比對。
SHEETS = (
    "sheet_id",
    "kind", "drawing_floor", "floor_from", "floor_to",
    "scale", "unit", "orientation",
    "drawing_no", "drawing_name", "tile_count",
    "frame_wkt", "title_block_wkt",
    "version_hint", "note",
)

# 【草案】ADR 0009：哪一片屬於哪一張圖、在網格的哪一格。
# row/col 從 0 起算，左上為 (0,0)。★ 網格形狀不固定 ——
# A2 可能是 1×2、A1 是 2×2、A0 可能是 2×4，**不要假設 N=4**。
SHEET_TILES = ("tile_id", "sheet_id", "row", "col", "part",
               "evidence", "conf", "status", "note")
TILE_PARTS = ("圖名區", "簽核區", "兩者皆有", "無")
TILE_STATUS = ("assigned", "ambiguous", "unassigned")

# 【草案】ADR 0011：片在圖座標系裡的位置（**候選，不是定案**）
# s01c_register 產出，由中樞裁定。dx/dy 是片的左上角在該張圖座標系的位置（px）。
# px_per_cm 每片各自校準 —— config.PX_PER_CM 只是後備值，不可跨案沿用
# （68 年案 1.1811 vs 79 年案實測約 1.02，差 13%）。
# tier 是證據強度：1 尺寸鏈跨縫閉合、2 圖框、3 基準線延續、4 重疊帶內容重複、
# 9 無錨點只好用網格標稱值。
PLACEMENT = ("tile_id", "sheet_id", "row", "col", "dx", "dy", "px_per_cm",
             "tier", "method", "evidence", "conf", "status", "note")
PLACEMENT_TIERS = (1, 2, 3, 4, 9)
PLACEMENT_STATUS = ("candidate", "conflict", "unresolved")

# 【草案】規格 §3：排除帶（圖框、標題欄、印章區）
EXCLUDE = ("exclude_id", "sheet_id", "kind", "bbox_wkt", "note")
EXCLUDE_KINDS = ("frame", "title_block", "stamp", "schedule", "other")

# 【草案】規格 §8：每 256px 區塊算對比度、雜訊、筆畫密度 → 分級。純統計無 AI。
QUALITY = (
    "quality_id", "sheet_id", "block_x", "block_y", "block_px",
    "contrast", "noise", "stroke_density", "level",
)
QUALITY_LEVELS = ("good", "shadow", "crease", "bleed")   # 【定版】規格 §8

# ─────────────────────────────────────────────────────────────
# 03 線段 / 文字 / 偵測 / 富標籤
# ─────────────────────────────────────────────────────────────
# 【草案】規格 §8：座標經 offsets 轉為整頁座標系後才寫檔
LINES = (
    "line_id", "sheet_id", "tile_id",
    "wkt", "length_px", "angle_deg", "thickness_px",
    "quality_zone",
)

# 【草案】裁決 §2：PaddleOCR-VL 跑每一片全圖；region 依 02_exclude 判定
TEXTS = (
    "text_id", "sheet_id", "tile_id",
    "text", "bbox_wkt", "angle_deg", "conf", "region",
)
TEXT_REGIONS = ("body", "title_block", "schedule")       # 【定版】裁決 §2

# 【定版（後五欄）】規格 §9 富標籤；【草案】其餘欄
# detector 欄填 rule_v1（裁決 §2）。status 一律由本層寫 proposed，
# 改成 adopted/rejected/uncertain 是 orchestrator 依 plan 回寫（§9、裁決 §4）。
RICH_LABEL = ("conf", "evidence", "provenance", "quality_zone", "status")
STATUS = ("proposed", "adopted", "rejected", "uncertain")  # 【定版】規格 §9

DETECTIONS = (
    "det_id", "sheet_id", "class_name",
    "bbox_wkt", "detector",
) + RICH_LABEL

ELEMENTS = (
    "element_id", "sheet_id", "class_name",
    "geom_wkt", "thickness_cm", "thickness_src",
    "source_lines",
) + RICH_LABEL

# 【定版】裁決 §6：由 ASSUMED 導出的值，thickness_src 填 "assumed"、信心 ≤ 0.4
THICKNESS_SRC = ("measured", "chain", "assumed")

# ─────────────────────────────────────────────────────────────
# 04 三源讀取
# ─────────────────────────────────────────────────────────────
# 【定版】裁決 §3 / 規格 §1.2 逐字
READINGS = (
    "id", "sheet_id", "kind", "value", "unit", "conf", "status",
    "src_paddle", "src_vlm", "src_geom",
    "bbox_x", "bbox_y", "bbox_w", "bbox_h", "crop",
    "verified_value", "verified_by", "verified_at", "note",
)
# 【定版】規格 §1.2 投票規則
VOTE_STATUS = ("green", "yellow", "red")
READING_SOURCES = ("src_paddle", "src_vlm", "src_geom")

# ─────────────────────────────────────────────────────────────
# 05 尺寸鏈
# ─────────────────────────────────────────────────────────────
# 【草案】規格 §7.1：chains 全部（含閉合狀態）會整包進中樞脈絡
CHAINS = (
    "chain_id", "sheet_id", "axis", "wkt",
    "sum_value", "total_value", "delta", "closed", "unit",
)
CHAIN_MEMBERS = ("chain_id", "seq", "reading_id", "value")

# ─────────────────────────────────────────────────────────────
# 06–08 校對 / 落地 / 矛盾
# ─────────────────────────────────────────────────────────────
# 【草案】規格 §3：人工校對後
VERIFIED = ("target", "target_id", "field", "old_value", "new_value",
            "verified_by", "verified_at", "note")

# 【草案】規格 §3。thickness_src=="assumed" 者信心 ≤ 0.4、輸出檔名帶 _draft（裁決 §6）
WALLS = ("wall_id", "sheet_id", "floor", "axis_wkt",
         "thickness_cm", "thickness_src", "height_cm", "height_src",
         "conf", "evidence", "note")
COLUMNS = ("column_id", "sheet_id", "floor", "outline_wkt",
           "w_cm", "d_cm", "size_src", "conf", "evidence", "note")

# 【定版】裁決 §5 逐字。append 模式，三來源共寫，靠 source 欄分。
CONFLICTS = ("conflict_id", "source", "kind", "severity", "sheet_id",
             "description", "involved_ids", "suggested_fix",
             "resolved", "resolved_by")
CONFLICT_SOURCES = ("chain_closure", "plan_vN", "cross_storey")  # plan_vN 見待決 #10

# 【草案】規格 §3
LOG = ("ts", "step", "case", "sheet_id", "level", "message")

# ─────────────────────────────────────────────────────────────
# plans/residuals_vN.csv  ★ 規格沒給欄位，但沒有它 residuals_all_handled 寫不出來
# ─────────────────────────────────────────────────────────────
# 【草案】依規格 §8 s08_compare 的職責推導：
#   「把 judgments 幾何投影回像素，算覆蓋率與未解釋粗線；
#     殘差落在 crease 區者自動註記」
# 這個檔不在 core.case.FILES（它按版本走 core.case.residuals_path(case_dir, n)）。
RESIDUALS = (
    "residual_id", "version", "sheet_id", "kind",
    "wkt",                 # 殘差在整頁座標系的位置
    "coverage",            # 該處被 judgments 覆蓋的比例，0–1
    "judgment_id",         # 若是「畫了但對不上」，指向該 judgment；未解釋粗線留空
    "involved_ids",        # 牽涉到的證據 id（命名空間#id，同 CONFLICTS.involved_ids）
    "quality_zone",        # crease 區者由 s08 自動註記（§8）
    "note",
)
RESIDUAL_KINDS = (
    "unexplained_stroke",  # 圖上有粗線，plan 沒有任何 judgment 解釋它
    "low_coverage",        # judgment 畫了，但投影回去蓋不住真線
    "over_reach",          # judgment 畫超出真線
)

# ─────────────────────────────────────────────────────────────
# 證據 id 命名空間  ★ 規格沒明說，但 §6.2 規則 2 需要它才實作得出來
# ─────────────────────────────────────────────────────────────
# plan 的 evidence / involved 寫的是 `命名空間#id`，例如
#   evidence: [pair#12, chain#c003]      involved: [chain#c007, read#p02_d0038]
#   overrides.label: det#x0101           uncertain.reason: (quality#q13)
# validate 規則 2「引用的 id 不存在於 CSV」要能把前綴解析到「哪個 CSV 的哪個 id 欄」。
# 【草案】—— 前綴字面取自規格 §6.1 的範例，對應關係由本檔代擬。
EVIDENCE_NS = {
    "line":    ("lines",         "line_id"),
    "pair":    ("detections",    "det_id"),      # 線對 → wall 候選，寫在 detections
    "det":     ("detections",    "det_id"),
    "elem":    ("elements",      "element_id"),
    "text":    ("texts",         "text_id"),
    "read":    ("readings",      "id"),
    "chain":   ("chains",        "chain_id"),
    "quality": ("quality",       "quality_id"),
    "exclude": ("exclude",       "exclude_id"),
    "sheet":   ("sheets",        "sheet_id"),
}
# 【定版】規格 §6.2 規則 3：座標只能追溯到 chain 或 measure
COORD_SOURCES = ("chain", "measure")

# ─────────────────────────────────────────────────────────────
# 對照表：core.case.FILES 的短名 → 本檔的欄位常數
# ─────────────────────────────────────────────────────────────
BY_FILE = {
    "offsets": OFFSETS, "sheets": SHEETS, "exclude": EXCLUDE, "quality": QUALITY,
    "sheet_tiles": SHEET_TILES,
    "lines": LINES, "texts": TEXTS, "detections": DETECTIONS, "elements": ELEMENTS,
    "readings": READINGS, "chains": CHAINS, "chain_members": CHAIN_MEMBERS,
    "verified": VERIFIED, "walls": WALLS, "columns": COLUMNS,
    "conflicts": CONFLICTS, "log": LOG,
}

# 每個 CSV 的 id 欄（給 validate 查 id 存在性用）
ID_COLUMN = {
    "offsets": "tile_id", "sheets": "sheet_id", "exclude": "exclude_id",
    "quality": "quality_id", "sheet_tiles": "tile_id",
    "lines": "line_id", "texts": "text_id",
    "detections": "det_id", "elements": "element_id", "readings": "id",
    "chains": "chain_id", "walls": "wall_id", "columns": "column_id",
    "conflicts": "conflict_id",
}
