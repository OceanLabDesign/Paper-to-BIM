#!/usr/bin/env python3
"""Paper-to-BIM 安裝程式 —— 偵測系統、裝好相依、產出一個可以按兩下的執行檔

    python3 install.py            # 安裝
    python3 install.py --check    # 只偵測不安裝
    python3 install.py --update   # 已裝過，只更新相依

macOS 與 Windows 都用同一支。使用者不必開終端機的話，
按兩下 `install.command`（macOS）或 `install.bat`（Windows）也一樣。

## 為什麼是安裝檔不是免安裝的執行檔

實測用 PyInstaller 把整個程式包起來，在這台開發機（conda 環境）產出
**1.1 GB** 的 .app —— conda 的 base 環境把 MKL 那類東西全拖了進去。
即使換乾淨的環境，光 opencv 就 160MB，包起來仍是好幾百 MB。

而且免安裝版還要處理兩個平台的簽章：macOS 未簽章的 .app 會被 Gatekeeper 擋、
Windows 未簽章的 .exe 會被 SmartScreen 擋，兩邊都要花錢買憑證才能根治。

安裝檔的作法是：**用使用者機器上的 Python 建一個獨立環境**，
只下載真正需要的套件（約 80MB），然後產出一個按兩下就開的啟動器。
更新也只要重跑一次，不必重新下載幾百 MB。

代價是**使用者要有 Python**。這支會偵測，沒有的話給出該平台的確切安裝指令。

## 這支只用標準函式庫

它要能在一台什麼都還沒裝的機器上跑起來 —— 所以自己不能有任何相依。
"""

import argparse
import os
import platform
import shutil
import subprocess
import sys
import venv
from pathlib import Path

ROOT = Path(__file__).resolve().parent
VENV = ROOT / ".venv"
APP_NAME = "Paper-to-BIM"
ENTRY = "tools/desktop.py"
PY_MIN, PY_MAX = (3, 10), (3, 14)      # 上下限來自 IfcOpenShell 與 rhino3dm
IS_WIN = os.name == "nt"
IS_MAC = sys.platform == "darwin"

OK, WARN, BAD = "✓", "!", "✗"


def say(mark, text, detail=""):
    print(f"  {mark} {text}" + (f"　{detail}" if detail else ""))


def rule(title):
    print(f"\n── {title} " + "─" * max(0, 58 - len(title) * 2))


def venv_python() -> Path:
    return VENV / ("Scripts" if IS_WIN else "bin") / ("python.exe" if IS_WIN else "python")


# ── 偵測 ─────────────────────────────────────────────────────────────────
def detect() -> dict:
    """把這台機器的狀況攤開。**不修東西，只回報。**"""
    rule("偵測系統")
    r = {"problems": [], "hints": []}

    r["os"] = platform.system()
    r["release"] = platform.release()
    r["arch"] = platform.machine()
    say(OK, f"作業系統　{r['os']} {r['release']}　{r['arch']}")

    v = sys.version_info
    r["python"] = f"{v.major}.{v.minor}.{v.micro}"
    r["python_ok"] = PY_MIN <= (v.major, v.minor) <= PY_MAX
    if r["python_ok"]:
        say(OK, f"Python　{r['python']}", sys.executable)
    else:
        say(BAD, f"Python {r['python']} 不在支援範圍 "
                 f"{PY_MIN[0]}.{PY_MIN[1]}–{PY_MAX[0]}.{PY_MAX[1]}")
        r["problems"].append("python_version")
        r["hints"].append(python_hint())

    # tkinter 是整個介面的基礎，而且**venv 不會補上它** ——
    # venv 的 tkinter 直接沿用底層 Python 的，底層沒有就是沒有。
    try:
        import tkinter
        root = tkinter.Tk()
        root.withdraw()
        r["tk"] = root.tk.call("info", "patchlevel")
        root.destroy()
        say(OK, f"tkinter　Tcl/Tk {r['tk']}")
    except Exception as exc:                          # noqa: BLE001
        r["tk"] = None
        say(BAD, "tkinter 不能用", f"{type(exc).__name__}: {exc}")
        r["problems"].append("tkinter")
        r["hints"].append(tk_hint())

    if shutil.which("git"):
        say(OK, "git", shutil.which("git"))
    else:
        say(WARN, "沒有 git（不影響執行，只影響之後更新程式）")

    free = shutil.disk_usage(ROOT).free / 1e9
    if free < 1.0:
        say(BAD, f"磁碟空間只剩 {free:.1f} GB，至少要 1 GB")
        r["problems"].append("disk")
    else:
        say(OK, f"磁碟空間　剩 {free:.1f} GB")

    if VENV.exists():
        say(WARN, f"已經有 {VENV.name}／（會沿用；要重來請加 --fresh）")
    r["has_venv"] = VENV.exists()

    # 選用：問 AI 那個功能靠本機的 Claude Code
    claude = shutil.which("claude")
    r["claude"] = claude
    say(OK if claude else WARN,
        "Claude Code CLI" + ("" if claude else "（沒有 → 校對頁的「問 AI」不能用，其餘正常）"),
        claude or "")
    return r


def python_hint() -> str:
    if IS_WIN:
        return ("安裝 Python 3.12：\n"
                "    winget install Python.Python.3.12\n"
                "  或到 https://www.python.org/downloads/windows/ 下載，\n"
                "  安裝時**務必勾選 tcl/tk and IDLE**（否則介面開不起來）。")
    if IS_MAC:
        return ("安裝 Python 3.12：\n"
                "    brew install python@3.12 python-tk@3.12\n"
                "  或到 https://www.python.org/downloads/macos/ 下載官方版\n"
                "  （官方版自帶 Tk，Homebrew 版要另外裝 python-tk）。")
    return "用你發行版的套件管理員裝 python3.12 與 python3-tk。"


def tk_hint() -> str:
    if IS_WIN:
        return ("重新執行 Python 安裝程式 → Modify → 勾選 **tcl/tk and IDLE**。")
    if IS_MAC:
        ver = f"{sys.version_info.major}.{sys.version_info.minor}"
        return (f"Homebrew 的 Python 要另外裝 Tk：\n"
                f"    brew install python-tk@{ver}\n"
                f"  或改用 python.org 的官方版（自帶 Tk）。")
    return "sudo apt install python3-tk    （Debian/Ubuntu）"


# ── 安裝 ─────────────────────────────────────────────────────────────────
def run(argv, **kw):
    p = subprocess.run(argv, **kw)
    if p.returncode != 0:
        raise SystemExit(f"\n✗ 指令失敗（離開碼 {p.returncode}）：{' '.join(map(str, argv))}")
    return p


def make_venv(fresh=False):
    rule("建立獨立環境")
    if fresh and VENV.exists():
        say(WARN, "刪掉舊的 .venv")
        shutil.rmtree(VENV)
    if VENV.exists():
        say(OK, "沿用現有的 .venv", str(VENV))
    else:
        # with_pip=True：有些系統的 Python 拆掉了 ensurepip，這裡會直接報錯而不是裝到一半才爆
        venv.EnvBuilder(with_pip=True, clear=False).create(VENV)
        say(OK, "建好 .venv", str(VENV))
    py = venv_python()
    if not py.exists():
        raise SystemExit(f"✗ 找不到 {py} —— .venv 建立失敗")
    return py


def install_deps(py: Path):
    rule("安裝相依套件")
    req = ROOT / "requirements.txt"
    if not req.exists():
        raise SystemExit(f"✗ 找不到 {req}")
    run([str(py), "-m", "pip", "install", "--upgrade", "pip", "--quiet"])
    say(OK, "pip 已更新")
    print("     下載中（約 80 MB，第一次比較久）…")
    run([str(py), "-m", "pip", "install", "-r", str(req), "--upgrade", "--quiet"])
    say(OK, "相依套件裝好了")


def verify(py: Path):
    rule("驗證")
    code = (
        "import sys, importlib\n"
        "for m in ('tkinter','cv2','numpy'):\n"
        "    importlib.import_module(m)\n"
        "import tkinter; r=tkinter.Tk(); r.withdraw()\n"
        "print(r.tk.call('info','patchlevel')); r.destroy()\n"
    )
    p = subprocess.run([str(py), "-c", code], capture_output=True, text=True)
    if p.returncode != 0:
        say(BAD, "環境驗證失敗")
        print(p.stderr[-800:])
        raise SystemExit(1)
    say(OK, f"tkinter / cv2 / numpy 都載得起來　Tcl/Tk {p.stdout.strip()}")

    p = subprocess.run([str(py), str(ROOT / ENTRY), "--selftest"],
                       capture_output=True, text=True, cwd=ROOT)
    tail = [x for x in p.stdout.splitlines() if "通過" in x]
    if p.returncode == 0:
        say(OK, "程式自測通過", tail[-1] if tail else "")
    else:
        say(WARN, "程式自測沒有全過（多半是還沒有案件資料，不影響安裝）",
            tail[-1] if tail else "")


# ── 產出啟動器 ───────────────────────────────────────────────────────────
def make_launcher(py: Path) -> Path:
    """做出使用者按兩下就能開的東西。

    不是 PyInstaller 那種「把 Python 也包進去」的執行檔 ——
    是一個指向 .venv 的啟動器。體積幾 KB，更新程式不必重做。
    """
    rule("產出執行檔")
    # ⚠ 啟動器一律走**相對路徑**。寫死絕對路徑的話，使用者把資料夾搬個位置
    #   （或改名）就整個壞掉，而且錯誤訊息完全看不出原因。
    if IS_WIN:
        # pythonw.exe 不會開主控台視窗；沒有的話退回 python.exe
        rel = r".venv\Scripts\pythonw.exe"
        if not (VENV / "Scripts" / "pythonw.exe").exists():
            rel = r".venv\Scripts\python.exe"
            say(WARN, "找不到 pythonw.exe，啟動時會閃一下主控台視窗")
        f = ROOT / f"{APP_NAME}.bat"
        f.write_bytes(
            ("@echo off\r\n"
             "rem Paper-to-BIM 啟動器（install.py 產生，可以重做）\r\n"
             'cd /d "%~dp0"\r\n'
             f'start "" "%~dp0{rel}" "{ENTRY}" %*\r\n').encode("utf-8"))
        say(OK, "已產出", str(f))
        say(WARN, "第一次開啟若被 SmartScreen 擋：更多資訊 → 仍要執行")
        return f

    f = ROOT / f"{APP_NAME}.command"
    f.write_text(
        "#!/bin/sh\n"
        "# Paper-to-BIM 啟動器（install.py 產生，可以重做）\n"
        'cd "$(dirname "$0")" || exit 1\n'
        f'exec ".venv/bin/python" "{ENTRY}" "$@"\n',
        encoding="utf-8")
    f.chmod(0o755)
    say(OK, "已產出", str(f))

    if IS_MAC:
        app = make_mac_app(py)
        say(OK, "也做了 .app（可以拖到 Dock）", str(app))
    return f


def make_mac_app(py: Path) -> Path:
    """最小的 .app —— 就是一個有 Info.plist 的資料夾，裡面放啟動用的 shell script。

    這樣圖示、Dock、Launchpad 都認得，而且**完全不需要 PyInstaller**。
    因為是本機產生的、不是網路下載的，所以沒有 quarantine 屬性，
    Gatekeeper 不會擋。
    """
    app = ROOT / f"{APP_NAME}.app"
    macos = app / "Contents" / "MacOS"
    macos.mkdir(parents=True, exist_ok=True)
    (app / "Contents" / "Info.plist").write_text(
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        '<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" '
        '"http://www.apple.com/DTDs/PropertyList-1.0.dtd">\n'
        '<plist version="1.0"><dict>\n'
        f'  <key>CFBundleName</key><string>{APP_NAME}</string>\n'
        f'  <key>CFBundleExecutable</key><string>{APP_NAME}</string>\n'
        '  <key>CFBundleIdentifier</key>'
        '<string>com.oceanlabdesign.papertobim</string>\n'
        '  <key>CFBundlePackageType</key><string>APPL</string>\n'
        '  <key>CFBundleShortVersionString</key><string>0.4.1</string>\n'
        # 不設這個的話 Retina 上整個介面會被放大成模糊的點陣
        '  <key>NSHighResolutionCapable</key><true/>\n'
        '</dict></plist>\n', encoding="utf-8")
    sh = macos / APP_NAME
    # 從 Contents/MacOS 往上三層就是專案根目錄 —— 用相對路徑，整包搬走也不會壞
    sh.write_text(
        "#!/bin/sh\n"
        'cd "$(dirname "$0")/../../.." || exit 1\n'
        f'exec ".venv/bin/python" "{ENTRY}" "$@"\n', encoding="utf-8")
    sh.chmod(0o755)
    return app


# ── 入口 ─────────────────────────────────────────────────────────────────
def main():
    ap = argparse.ArgumentParser(description="Paper-to-BIM 安裝程式")
    ap.add_argument("--check", action="store_true", help="只偵測，不安裝")
    ap.add_argument("--update", action="store_true", help="只更新相依套件")
    ap.add_argument("--fresh", action="store_true", help="砍掉 .venv 重來")
    a = ap.parse_args()

    print(f"\n{APP_NAME} 安裝程式")
    print(f"專案目錄：{ROOT}")

    r = detect()
    if r["problems"]:
        rule("要先處理這些")
        for h in r["hints"]:
            print("  " + h.replace("\n", "\n  "))
        if "disk" in r["problems"]:
            print("  清出至少 1 GB 空間再重跑。")
        print("\n處理完之後重新執行這支。")
        return 1
    if a.check:
        print("\n偵測完畢，沒有阻擋安裝的問題。要安裝請不加 --check 再跑一次。")
        return 0

    py = make_venv(fresh=a.fresh)
    install_deps(py)
    verify(py)
    if not a.update:
        launcher = make_launcher(py)
    else:
        launcher = ROOT / (f"{APP_NAME}.bat" if IS_WIN else f"{APP_NAME}.command")

    rule("完成")
    print(f"  按兩下 {launcher.name} 就可以開始用。")
    print(f"  或在終端機：{venv_python()} {ENTRY}")
    if not r["claude"]:
        print("\n  提醒：校對頁的「問 AI」需要本機裝好 Claude Code（claude 指令）。")
        print("  其餘功能不受影響。")
    print()
    return 0


if __name__ == "__main__":
    sys.exit(main())
