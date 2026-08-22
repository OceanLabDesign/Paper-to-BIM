"""骨架煙霧測試 —— `python3 tests/smoke.py`（從 repo root 執行）

檢查三件事：
  1. 每支模組都 import 得起來（骨架接得上，stub 只在**呼叫時**才炸）
  2. core/config.py 的實測值沒有被「順手優化」（§10 逐項比對）
  3. 建造順序（§11）第 1 步：契約三件套寫了沒
  4. 契約自洽：fields 與 case 對得上、EVIDENCE_NS 指得到、§9 五欄齊、classes 15 類且順序即 id
  5. plan_schema 與 §6.1 範例對得上（需 PyYAML，沒有就跳過）
  6. 最小測資：欄位對得上契約、403+403=806 閉合、evidence id 解析得到
  7. 新接縫：TOOL_SPECS 與 tools.py 對得上、匯出器中繼資料合法、
     IFC 仍被 §12 擋著、沒有任何 exporter 相依 MCP
  8. ADR：前置資料合法、編號不重用、必要段落齊、README 索引沒漏
  9. 逐字區塊：§7.3 的 prompt 與 §5 的迴圈，程式與規格必須仍一字不差
各項獨立計分 —— 任一項失敗不會污染其他項的判定。
除了 [5] 的 PyYAML 之外不需要第三方套件。
"""

import ast
import importlib
import sys
from pathlib import Path

sys.dont_write_bytecode = True   # 不留 .pyc：產生器改動後大小若沒變，
                                 # 位元碼快取會讓本腳本讀到舊版（實際踩過）
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
    "planning.llm.base", "planning.llm.anthropic", "planning.llm.openai_compat",
    "planning.llm.registry", "planning.skills",
    "execution.s07_execute", "execution.s08_compare",
    "execution.exporters.base", "execution.exporters.dxf", "execution.exporters.rhino",
    "execution.exporters.visualarq", "execution.exporters.archicad",
    "execution.exporters.revit", "execution.exporters.ifc",
    "execution.exporters.registry",
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

# [4] 契約自洽 —— 只在契約寫了之後才查
contract_fail = []
if "core/fields.py" not in empty:
    fields = importlib.import_module("core.fields")
    case = importlib.import_module("core.case")
    for k in case.FILES:
        if k not in fields.BY_FILE:
            contract_fail.append(f"case.FILES 有 {k!r}，fields.BY_FILE 沒有")
    for k in fields.BY_FILE:
        if k not in case.FILES:
            contract_fail.append(f"fields.BY_FILE 有 {k!r}，case.FILES 沒有")
    for ns, (fk, col) in fields.EVIDENCE_NS.items():
        if fk not in fields.BY_FILE:
            contract_fail.append(f"EVIDENCE_NS[{ns!r}] 指向不存在的檔 {fk!r}")
        elif col not in fields.BY_FILE[fk]:
            contract_fail.append(f"EVIDENCE_NS[{ns!r}] 指向 {fk} 沒有的欄 {col!r}")
    for col in fields.RICH_LABEL:                      # §9 富標籤五欄
        for t in ("DETECTIONS", "ELEMENTS"):
            if col not in getattr(fields, t):
                contract_fail.append(f"§9 富標籤欄 {col!r} 不在 fields.{t}")
    for src in fields.CONFLICT_SOURCES:                # 裁決 §5 三來源
        if src not in ("chain_closure", "plan_vN", "cross_storey"):
            contract_fail.append(f"CONFLICT_SOURCES 多出 {src!r}（裁決 §5 只有三個）")
if "core/classes.py" not in empty:
    C = importlib.import_module("core.classes")
    if len(C.CLASSES) != 15:                           # §4：15 類
        contract_fail.append(f"classes 是 {len(C.CLASSES)} 類，§4 說 15 類")
    if len(set(C.NAMES)) != len(C.NAMES):
        contract_fail.append("classes 有重複的 name")
    for n, _zh, t in C.CLASSES:
        if t not in C.TIERS:
            contract_fail.append(f"class {n!r} 的 tier {t!r} 不合法")
    for n in ("wall", "column", "dim_line"):           # §8 規則式偵測三條逐字指名
        if not C.is_valid(n):
            contract_fail.append(f"§8 點名的類別 {n!r} 不在 classes")
    for i, (n, _zh, _t) in enumerate(C.CLASSES):       # 順序即 id
        if C.class_id(n) != i:
            contract_fail.append(f"class_id({n!r}) 不等於它的位置 {i}")
print(f"[4] 契約自洽：{'通過' if not contract_fail else '有問題'}"
      + ("" if "core/fields.py" not in empty else "（fields.py 還沒寫，跳過）"))

# [5] plan_schema vs §6.1 範例 —— 需要 PyYAML，沒有就跳過
schema_fail = []
if "core/plan_schema.py" not in empty:
    try:
        import yaml
    except ImportError:
        print("[5] plan_schema 對照 §6.1 範例：跳過（無 PyYAML）")
    else:
        ps = importlib.import_module("core.plan_schema")
        d = yaml.safe_load((ROOT / "examples/plan_vN.sample.yaml").read_text(encoding="utf-8"))
        for sec in ps.SECTIONS:
            if sec not in d:
                schema_fail.append(f"§6.1 範例缺區塊 {sec!r}")
        for k in d:
            if k not in ps.SECTIONS:
                schema_fail.append(f"§6.1 範例多出區塊 {k!r}，SECTIONS 沒收錄")
        if tuple(d.get("context", {})) != ps.CONTEXT_KEYS:
            schema_fail.append(f"context 鍵不符：範例 {tuple(d.get('context', {}))} vs schema {ps.CONTEXT_KEYS}")
        for j in d.get("judgments", []):
            for k in ps.JUDGMENT_REQUIRED:
                if k not in j:
                    schema_fail.append(f"judgment {j.get('id')} 缺必填鍵 {k!r}")
            if len(j.get("evidence", [])) < ps.MIN_EVIDENCE:
                schema_fail.append(f"judgment {j.get('id')} 的 evidence 少於 {ps.MIN_EVIDENCE}")
        for r in d.get("residual_handling", []):
            if r.get("action") not in ps.RESIDUAL_ACTIONS:
                schema_fail.append(f"residual action {r.get('action')!r} 不在 {ps.RESIDUAL_ACTIONS}")
        if len(ps.REJECT_RULES) != 6:
            schema_fail.append(f"§6.2 是六條，REJECT_RULES 有 {len(ps.REJECT_RULES)} 條")
        print(f"[5] plan_schema 對照 §6.1 範例：{'一致' if not schema_fail else '有出入'}")

# [6] 最小測資：欄位對得上契約、尺寸鏈閉合、evidence 解析得到
fixture_fail = []
if "core/fields.py" not in empty:
    import csv
    sys.path.insert(0, str(ROOT / "tests" / "fixtures"))
    import make_case_min
    fields = importlib.import_module("core.fields")
    case = importlib.import_module("core.case")
    try:
        fx = make_case_min.build()                  # 冪等：照 fields.py 重生一次

        for key in make_case_min.ROWS:
            with case.path(fx, key).open(encoding="utf-8") as f:
                header = tuple(next(csv.reader(f)))
            if header != tuple(fields.BY_FILE[key]):
                fixture_fail.append(f"測資 {key} 的欄位與 core.fields 不符")

        def rows(key):
            with case.path(fx, key).open(encoding="utf-8") as f:
                return list(csv.DictReader(f))

        # §11 第 4 步的第一筆迴歸測試：403 + 403 = 806，且鏈閉合
        members = [r for r in rows("chain_members") if r["chain_id"] == "c001"]
        chain = next(r for r in rows("chains") if r["chain_id"] == "c001")
        parts = [float(m["value"]) for m in members]
        if sum(parts) != float(chain["total_value"]):
            fixture_fail.append(f"尺寸鏈 c001：{'+'.join(str(int(p)) for p in parts)}"
                                f" = {sum(parts):.0f}，但 total_value 是 {chain['total_value']}")
        if float(chain["delta"]) != 0 or chain["closed"] != "1":
            fixture_fail.append(f"尺寸鏈 c001 應為閉合（delta=0, closed=1），實際 "
                                f"delta={chain['delta']} closed={chain['closed']}")

        # §6.2 規則 2 的前置：每個 `命名空間#id` 都要解析得到，且該 id 真的在 CSV 裡
        index = {k: {r[fields.ID_COLUMN[k]] for r in rows(k)}
                 for k in make_case_min.ROWS if k in fields.ID_COLUMN}
        if "core/classes.py" not in empty:              # 測資的類別必須合法
            C = importlib.import_module("core.classes")
            for key in ("detections", "elements"):
                for r in rows(key):
                    if not C.is_valid(r["class_name"]):
                        fixture_fail.append(f"測資 {key} 的 class_name "
                                            f"{r['class_name']!r} 不在 core.classes")
        for key in ("detections", "elements"):
            for r in rows(key):
                for ref in filter(None, r["evidence"].split("|")):
                    ns, _, rid = ref.partition("#")
                    if ns not in fields.EVIDENCE_NS:
                        fixture_fail.append(f"{key} 的 evidence {ref!r}：前綴不在 EVIDENCE_NS")
                        continue
                    fk, _col = fields.EVIDENCE_NS[ns]
                    if rid not in index.get(fk, set()):
                        fixture_fail.append(f"{key} 的 evidence {ref!r}：{fk} 裡查無此 id")
    except Exception as exc:                        # 契約改了、測資沒跟上
        fixture_fail.append(f"測資重建失敗（契約與測資不同步）：{type(exc).__name__}: {exc}")

    n = sum(len(v) for v in make_case_min.ROWS.values())
    print(f"[6] 最小測資（403+403=806）：{'通過' if not fixture_fail else '有問題'}"
          f"（{len(make_case_min.ROWS)} 個 CSV／{n} 列）")

# [7] 新接縫：工具規格、匯出器、技能
seam_fail = []
if not import_fail:
    import inspect
    tools = importlib.import_module("planning.tools")
    fns = {n for n, o in vars(tools).items() if inspect.isfunction(o)}
    spec_names = set(tools.TOOL_NAMES)
    for n in spec_names - fns:
        seam_fail.append(f"TOOL_SPECS 有 {n!r} 但 planning/tools.py 沒有這支函式")
    for n in fns - spec_names:
        seam_fail.append(f"planning/tools.py 有 {n!r} 但 TOOL_SPECS 沒有它的規格")

    exbase = importlib.import_module("execution.exporters.base")
    exreg = importlib.import_module("execution.exporters.registry")
    for r in exreg.table():
        if r["needs"] not in exbase.NEEDS:
            seam_fail.append(f"匯出器 {r['name']!r} 的 needs {r['needs']!r} 不合法")
        if not isinstance(r["native"], bool):
            seam_fail.append(f"匯出器 {r['name']!r} 的 native_objects 不是 bool")
        if r["os"] not in ("", "windows", "darwin", "linux"):
            seam_fail.append(f"匯出器 {r['name']!r} 的 os_required {r['os']!r} 不合法")
        if r["gated"] and not exreg.EXPORTERS[r["name"]].gate_reason:
            seam_fail.append(f"匯出器 {r['name']!r} 被擋卻沒說理由")
    if not next(x for x in exreg.table() if x["name"] == "ifc")["gated"]:
        seam_fail.append("IFC 匯出器沒有被擋 —— §12 說等 ArchiCAD 往返測試通過才做")
    # MCP 不得成為 exporter 的相依（§8 確定性）—— 只准出現在 docstring
    for f in sorted((ROOT / "execution" / "exporters").glob("*.py")):
        for ln, line in enumerate(f.read_text(encoding="utf-8").splitlines(), 1):
            t = line.strip()
            if (t.startswith("import ") or t.startswith("from ")) and "mcp" in t.lower():
                seam_fail.append(f"{f.name}:{ln} 匯入了 MCP —— §8：確定性管線不准插非確定性元件")

    sk = importlib.import_module("planning.skills")
    for x in sk.list_skills():
        if not x["description"]:
            seam_fail.append(f"技能 {x['name']!r} 的 SKILL.md 缺 description")
    print(f"[7] 新接縫：{'通過' if not seam_fail else '有問題'}"
          f"（{len(spec_names)} 支工具／{len(exreg.table())} 個匯出器／{len(sk.list_skills())} 個技能）")

# [8] ADR：前置資料合法、編號與檔名一致、必要段落齊、索引沒漏
adr_fail = []
adr_dir = ROOT / "docs" / "adr"
if adr_dir.exists():
    import re
    STATUSES = ("proposed", "accepted", "superseded", "rejected")
    SECTIONS = ("## 脈絡", "## 選項", "## 決定", "## 後果", "## 依據")
    index = (adr_dir / "README.md").read_text(encoding="utf-8")
    seen = {}
    adrs = sorted(adr_dir.glob("[0-9]*.md"))
    for f in adrs:
        t = f.read_text(encoding="utf-8")
        m = re.match(r"---\n(.*?)\n---\n", t, re.S)
        if not m:
            adr_fail.append(f"{f.name}：沒有前置資料")
            continue
        meta = dict((k.strip(), v.strip())
                    for k, _, v in (l.partition(":") for l in m.group(1).splitlines()) if k.strip())
        num = meta.get("number", "")
        if num != f.name[:4]:
            adr_fail.append(f"{f.name}：number={num!r} 與檔名不符")
        if num in seen:
            adr_fail.append(f"{f.name}：編號 {num} 與 {seen[num]} 重複（編號永不重用）")
        seen[num] = f.name
        if meta.get("status") not in STATUSES:
            adr_fail.append(f"{f.name}：status {meta.get('status')!r} 不在 {STATUSES}")
        if meta.get("status") == "superseded" and not meta.get("superseded_by"):
            adr_fail.append(f"{f.name}：標為 superseded 卻沒填 superseded_by")
        for sec in SECTIONS:
            if sec not in t:
                adr_fail.append(f"{f.name}：缺 {sec} 段")
        if f.name not in index:
            adr_fail.append(f"{f.name}：沒出現在 docs/adr/README.md 的索引")
    print(f"[8] ADR：{'通過' if not adr_fail else '有問題'}（{len(adrs)} 份）")

# [9] 逐字區塊守門：規格裡逐字轉錄的東西，程式與文件必須仍然一字不差
verbatim_fail = []
spec_path = ROOT / "docs" / "程式設計_v0.4.md"
if spec_path.exists() and not import_fail:
    spec = spec_path.read_text(encoding="utf-8")

    # §7.3 system prompt —— 純逐字，沒有任何改寫餘地
    prompts = importlib.import_module("planning.prompts")
    for line in prompts.SYSTEM_PROMPT.strip().splitlines():
        if line and line not in spec:
            verbatim_fail.append(f"§7.3 prompt 這行在規格裡找不到：{line[:36]}…")

    # §5 迴圈骨架 —— 比對「語句序列」（去註解、去縮排），
    # 已知的刻意差異只有 MAX_ITER 改成從 core.config 匯入
    def statements(text, start):
        out, on = [], False
        for ln in text.splitlines():
            if ln.strip().startswith("def run_case"):
                on = True; continue
            if on:
                if ln.strip().startswith(("def ", "#", "```")) and ln[:1] not in (" ", "\t"):
                    break
                code = ln.split("#")[0].strip()
                if code:
                    out.append(code)
        return out
    a = statements(spec, "§5")
    b = statements((ROOT / "planning" / "orchestrator.py").read_text(encoding="utf-8"), "code")
    if a != b:
        only_spec = [x for x in a if x not in b]
        only_code = [x for x in b if x not in a]
        verbatim_fail.append(
            f"§5 迴圈與 orchestrator.run_case 不一致："
            f"只在規格 {only_spec or '無'}；只在程式 {only_code or '無'}")
    print(f"[9] 逐字區塊：{'一致' if not verbatim_fail else '有出入'}"
          f"（§7.3 prompt {len(prompts.SYSTEM_PROMPT.strip().splitlines())} 行、§5 迴圈 {len(b)} 句）")

failures = (import_fail + config_fail + contract_fail + schema_fail
            + fixture_fail + seam_fail + adr_fail + verbatim_fail)
if failures:
    print("\n✗ 有問題：")
    for f in failures:
        print("  -", f)
    sys.exit(1)
print("\n✓ 骨架完整。" + ("下一步：§11 第 1 步，負責人手寫契約三件套。" if empty else ""))
