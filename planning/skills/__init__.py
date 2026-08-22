"""planning/skills —— 中樞的技能包

一個技能＝一個資料夾，裡面：
    SKILL.md   **必要**。開頭是 name/description 兩行前置資料，其後是指令內文。
    run.py     選用。若有，需提供 run(case_dir, **kw)，中樞可當工具呼叫。

為什麼是「按需載入」而不是全部塞進 system prompt：
§7.1 脈絡節食 —— 中樞脈絡裡平常**只放技能名與一行描述**，
碰到對應情境才 load() 全文。技能多了也不會撐爆脈絡。

新增技能＝新增一個資料夾。不必改這支，不必改中樞。
"""

import importlib.util
from pathlib import Path

ROOT = Path(__file__).resolve().parent


def _front_matter(md: str) -> dict:
    """讀 SKILL.md 開頭的 `name:` / `description:`。不引 PyYAML，維持零相依。"""
    meta = {}
    for line in md.splitlines():
        line = line.strip()
        if line in ("---", ""):
            continue
        if ":" not in line:
            break
        key, _, val = line.partition(":")
        key = key.strip()
        if key not in ("name", "description"):
            break
        meta[key] = val.strip()
        if len(meta) == 2:
            break
    return meta


def list_skills() -> list:
    """回傳 [{name, description, dir, has_code}]，給中樞脈絡用的清單（不含內文）。"""
    out = []
    for d in sorted(ROOT.iterdir()):
        md = d / "SKILL.md"
        if not d.is_dir() or not md.exists():
            continue
        meta = _front_matter(md.read_text(encoding="utf-8"))
        out.append({"name": meta.get("name", d.name),
                    "description": meta.get("description", ""),
                    "dir": d,
                    "has_code": (d / "run.py").exists()})
    return out


def load_skill(name: str) -> str:
    """回傳 SKILL.md 全文，供中樞放進脈絡。"""
    md = ROOT / name / "SKILL.md"
    if not md.exists():
        raise KeyError(f"沒有技能 {name!r}；可用：{[s['name'] for s in list_skills()]}")
    return md.read_text(encoding="utf-8")


def run_skill(name: str, case_dir, **kw):
    """執行技能的 run.py。**唯讀**：與 planning/tools.py 同一條紀律 ——
    技能不准寫任何 CSV，產出要經中樞放進 plan、經 validate 才算數（§7.4）。
    """
    path = ROOT / name / "run.py"
    if not path.exists():
        raise KeyError(f"技能 {name!r} 沒有 run.py（只有指令，沒有可執行部分）")
    spec = importlib.util.spec_from_file_location(f"skill_{name}", path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod.run(case_dir, **kw)
