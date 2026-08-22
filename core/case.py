"""core/case.py —— 案件資料夾結構

規格：v0.4 §3 逐條轉錄。一個案子一個資料夾；每步讀檔寫檔；編號即順序。

本模組**只管路徑，不管內容**。欄位一律引 core/fields.py，類別一律引 core/classes.py。
這是全 repo 唯一該出現檔名字串的地方 —— 其他模組請用 path()/plan_path()/residuals_path()，
不要自己拼 "03_lines.csv"，避免各步驟對檔名各寫一份而漂移。
"""

from pathlib import Path

# §3 的子資料夾
DIRS = (
    "00_raw",        # 原始 PDF（唯讀）
    "01_tiles",           # s01 拆出的 A3 片（原始解析度、**未轉正**，可追溯用，永不覆蓋）
    "01_tiles_upright",   # s01b 轉正後的片（裁決 §1）—— s02 以後一律吃這個
    "01_rectified",  # 轉正後整頁（僅供人看；程式吃 tiles+offsets）
    "04_crops",
    "plans",         # 中樞的思考史：plan_vN.yaml / residuals_vN.csv
    "out",           # 一樓平面.dxf …
)

# §3 的檔案。key 是程式用的短名，value 是磁碟上的真名。
FILES = {
    "offsets":       "01_offsets.csv",   # 放置矩陣＋rotation＋upright_file（裁決 §1）
    "sheets":        "02_sheets.csv",    # 圖種/樓層/比例/單位/方向/圖框範圍/版本
    "exclude":       "02_exclude.csv",   # 排除帶（圖框、標題欄、印章區）
    "quality":       "02_quality.csv",   # 品質地圖（分區塊：對比度/雜訊/可信度）
    "lines":         "03_lines.csv",
    "texts":         "03_texts.csv",
    "detections":    "03_detections.csv",
    "elements":      "03_elements.csv",
    "readings":      "04_readings.csv",
    "chains":        "05_chains.csv",
    "chain_members": "05_chain_members.csv",
    "verified":      "06_verified.csv",  # 人工校對後
    "walls":         "07_walls.csv",
    "columns":       "07_columns.csv",
    "conflicts":     "08_conflicts.csv",  # append 模式，三個來源共寫，靠 source 欄分（裁決 §5）
    "log":           "log.csv",
}


def path(case_dir, key) -> Path:
    """取案件內某個 CSV 的路徑。key 用 FILES 的短名。"""
    if key not in FILES:
        raise KeyError(f"{key!r} 不在 core/case.py 的 FILES；§3 沒有這個檔，不要自行新增")
    return Path(case_dir) / FILES[key]


def dir_path(case_dir, name) -> Path:
    """取案件內某個子資料夾的路徑。"""
    if name not in DIRS:
        raise KeyError(f"{name!r} 不在 core/case.py 的 DIRS；§3 沒有這個資料夾")
    return Path(case_dir) / name


def plan_path(case_dir, version: int) -> Path:
    """plans/plan_vN.yaml"""
    return Path(case_dir) / "plans" / f"plan_v{version}.yaml"


def residuals_path(case_dir, version: int) -> Path:
    """plans/residuals_vN.csv"""
    return Path(case_dir) / "plans" / f"residuals_v{version}.csv"


def ensure_case(case_dir) -> Path:
    """建立 §3 的空資料夾骨架（已存在則不動）。只建資料夾，不碰任何 CSV。"""
    case_dir = Path(case_dir)
    for d in DIRS:
        (case_dir / d).mkdir(parents=True, exist_ok=True)
    return case_dir
