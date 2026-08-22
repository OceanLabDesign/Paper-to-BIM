"""骨架煙霧測試 —— `python3 tests/smoke.py`（從 repo root 執行）

檢查三件事：
  1. 每支模組都 import 得起來（骨架接得上，stub 只在**呼叫時**才炸）
  2. core/config.py 的實測值沒有被「順手優化」（§10 逐項比對）
  3. 建造順序（§11）第 1 步：契約三件套寫了沒
三項各自獨立計分 —— 任一項失敗不會污染另外兩項的判定。
不需要任何第三方套件。
"""

import ast
import importlib
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

MODULES = [
    "core.config", "core.case", "core.io",
    "core.fields", "core.classes", "core.plan_schema",
    "perception.s01_ingest", "perception.s01b_orient", "perception.s02_layout",
    "perception.s02b_quality", "perception.s03_lines", "perception.s03_detect",
    "perception.s03_texts", "perception.s03_elements", "perception.s04_read",
    "perception.s05_solve", "perception.run_passive",
    "perception.detectors.rule", "perception.detectors.yolo",
    "planning.orchestrator", "planning.proposer", "planning.fake_proposer", "planning.validate",
    "planning.context", "planning.prompts", "planning.tools",
    "planning.subagents.arbiter", "planning.subagents.detective",
    "execution.s07_execute", "execution.s08_compare",
    "review.s09_crosscheck", "review.export_review",
]

# §10 實測校準參數。改這裡之前先確認有新的實測結果。
EXPECTED_CONFIG = {
    "UNIT": "cm", "SCALE": 100, "DPI": 300,
    "ADAPTIVE_BLOCK": 31, "ADAPTIVE_C": 12,
    "HOUGH_THRESHOLD": 60, "MIN_LINE_LENGTH": 60, "MAX_LINE_GAP": 6,
    "WALL_GAP_PX": (12, 42), "MAX_ITER": 3,
    "ASSUMED_SRC": "assumed", "ASSUMED_MAX_CONF": 0.4, "DRAFT_SUFFIX": "_draft",
    "ASSUMED": {"層高cm_1F": 400, "層高cm_其他": 320,
                "牆厚cm_外": 24, "牆厚cm_內": 12, "板厚cm": 15},
}

CONTRACTS = ("core/fields.py", "core/classes.py", "core/plan_schema.py")

import_fail, config_fail = [], []

# [1] import
for name in MODULES:
    try:
        importlib.import_module(name)
    except Exception as exc:
        import_fail.append(f"import {name}: {exc!r}")
print(f"[1] import：{len(MODULES) - len(import_fail)}/{len(MODULES)} 支模組 OK")

# [2] §10 參數 —— 只看 config，不受 [1] 影響
cfg = importlib.import_module("core.config")
for key, want in EXPECTED_CONFIG.items():
    got = getattr(cfg, key, None)
    if got != want:
        config_fail.append(f"config.{key} = {got!r}，§10 是 {want!r}")
if abs(cfg.PX_PER_CM - 1.1811023622047243) > 1e-9:
    config_fail.append(f"config.PX_PER_CM = {cfg.PX_PER_CM!r}，§10 換算應 ≈1.181")
print(f"[2] §10 實測參數：{'一致' if not config_fail else '有出入'}"
      f"（PX_PER_CM={cfg.PX_PER_CM:.4f}、牆24cm≈{24 * cfg.PX_PER_CM:.0f}px、"
      f"總寬806cm≈{806 * cfg.PX_PER_CM:.0f}px）")

# [3] §11 第 1 步 —— 用 AST 判斷「docstring 以外有沒有實際定義」，
#     不能用「模組裡有沒有符號」：一行 import 就會讓空契約被誤判成已寫。
def has_definitions(rel_path: str) -> bool:
    tree = ast.parse((ROOT / rel_path).read_text(encoding="utf-8"))
    for node in tree.body:
        if isinstance(node, ast.Expr) and isinstance(node.value, ast.Constant) \
                and isinstance(node.value.value, str):
            continue                                    # docstring
        if isinstance(node, (ast.Import, ast.ImportFrom)):
            continue                                    # 只有 import 不算寫了契約
        return True
    return False

empty = [c for c in CONTRACTS if not has_definitions(c)]
print(f"[3] §11 第 1 步 契約三件套：{len(CONTRACTS) - len(empty)}/{len(CONTRACTS)} 已寫"
      + (f"（{'、'.join(Path(c).stem for c in empty)} 還是空的）" if empty else ""))

failures = import_fail + config_fail
if failures:
    print("\n✗ 有問題：")
    for f in failures:
        print("  -", f)
    sys.exit(1)
print("\n✓ 骨架完整。" + ("下一步：§11 第 1 步，Louis 手寫契約三件套。" if empty else ""))
