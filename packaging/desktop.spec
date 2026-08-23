# -*- mode: python ; coding: utf-8 -*-
"""PyInstaller spec —— Paper-to-BIM 工作站

    python3 -m PyInstaller packaging/desktop.spec --noconfirm

macOS 產出 `dist/Paper-to-BIM.app`，Windows 產出 `dist/Paper-to-BIM/Paper-to-BIM.exe`。
**同一份 spec 兩邊共用**，平台差異都在 `IS_MAC` / `IS_WIN` 分支裡。

## 為什麼是 onedir 不是 onefile

onefile 每次啟動都要把整包解壓到暫存目錄。官方文件（operating-mode.html）自己寫
「one-file app is a little slower to start than a one-folder app」，而且程式被強制
結束時暫存資料夾不會清掉。macOS 的 .app 本來就是目錄形式，官方也明講
`--onefile` 加 `--windowed` 產 .app 「is not recommended」。

## 使用者的案件不在包裡

`cases/` 是使用者資料，**不打包**。程式用 `tools/desktop.py` 的 `app_dir()` 去找：
環境變數 `PAPER_TO_BIM_HOME` → 執行檔旁邊 → `~/Documents/Paper-to-BIM`。
介面上也有「換資料夾…」讓使用者自己指。

## 在被同步的資料夾裡打包，ad-hoc 簽章會失敗

實測在 `~/Desktop/...` 底下打包，PyInstaller 的自動 ad-hoc 簽章會報

    resource fork, Finder information, or similar detritus not allowed

原因是 .app 目錄本身被掛上了 `com.apple.FinderInfo` 與
`com.apple.fileprovider.fpfs#P` —— 有檔案同步服務（iCloud Drive／Dropbox 之類）
在同步這個資料夾，`xattr -c` 清掉之後它會再補回來。

**這是本機環境問題，不是建置問題**：程式照常跑得起來（實測凍結版 selftest 7/7），
而且 CI 的乾淨 checkout 沒有檔案同步，不會發生。
本機要拿到簽好的包，打到沒有被同步的位置：

    python -m PyInstaller packaging/desktop.spec --noconfirm --distpath ~/pb-dist

## 打包環境：不要用 conda 的直譯器（interpreter）直接打

conda 的 numpy 連著 Intel MKL，PyInstaller 會把 30 幾支 libmkl_*.dylib（合計約
886MB）收進包裡。用 `python -m venv` + PyPI 的 wheel 就沒有這件事。
建置步驟見 README 的「自己打一版」。
"""

import platform
import sys
from pathlib import Path

IS_MAC = sys.platform == "darwin"
IS_WIN = sys.platform == "win32"
ROOT = Path(SPECPATH).parent          # noqa: F821  （SPECPATH 由 PyInstaller 注入）
NAME = "Paper-to-BIM"

# 延遲匯入的東西 PyInstaller 的靜態分析可能漏掉，明列出來。
# planning.llm.* 是在 review.Review.ask() 裡面才 import 的（問 AI 才用得到）。
# cv2 / numpy / tkinter 其實各自有官方 hook（hook-cv2.py、hook-numpy.py、
# hook-_tkinter.py）會處理，留在這裡只是保險，不是必要。
HIDDEN = [
    "cv2", "numpy",
    "planning.llm.registry", "planning.llm.base",
    "planning.llm.claude_cli", "planning.llm.anthropic", "planning.llm.openai_compat",
    "core.fields", "core.classes",
    "tkinter", "tkinter.ttk", "tkinter.font", "tkinter.filedialog",
]

# 這些沒用到但常被連帶拖進來，排掉可以省不少體積
EXCLUDE = [
    "matplotlib", "scipy", "pandas", "IPython", "jupyter", "notebook",
    "PyQt5", "PyQt6", "PySide2", "PySide6", "wx",
    "torch", "tensorflow", "sklearn", "sympy",
    "pytest", "setuptools", "pip", "test", "unittest",
]

a = Analysis(                                                    # noqa: F821
    [str(ROOT / "tools" / "desktop.py")],
    pathex=[str(ROOT)],
    binaries=[],
    datas=[],                        # cases/ 是使用者資料，刻意不打包
    hiddenimports=HIDDEN,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=EXCLUDE,
    noarchive=False,
    optimize=0,
)

# ── 丟掉 OpenCV 的 FFmpeg DLL ────────────────────────────────────────────
# Windows 的 opencv wheel（headless 版也一樣）內含 opencv_videoio_ffmpeg*_64.dll，
# 4.14.0.94 實測 30.5MB。hook-cv2 的 collect_dynamic_libs('cv2') 會把它一起收進來。
# 本專案全程沒有 VideoCapture / VideoWriter / imshow（全 repo grep 過，零命中），
# 只用 imread / imwrite / imencode / resize 與繪圖，這支 DLL 是純死重量；
# cv2 對它是「用到才 LoadLibrary」，不載不會 ImportError。
# 比對前綴不含版本號，所以 opencv 升版仍然命中。macOS 的 wheel 沒有這支，不受影響。
a.binaries = [b for b in a.binaries if "opencv_videoio_ffmpeg" not in b[0].lower()]

pyz = PYZ(a.pure)                                                # noqa: F821

exe = EXE(                                                       # noqa: F821
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name=NAME,
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    # UPX 對 Python 打包省不了多少，卻常被防毒誤判成加殼惡意程式，所以關掉。
    # 另外官方文件寫「UPX is currently used only on Windows」，macOS 根本不會套用。
    upx=False,
    console=False,                   # 不要跳出主控台視窗
    disable_windowed_traceback=False,
    # ⚠ argv_emulation 一定要 False。官方 feature-notes 對 onedir 的警告原文：
    #   「The initial event processing performed by bootloader in onedir mode may
    #    interfere with UI toolkit used by frozen python application, such as
    #    Tcl/Tk via tkinter module. The symptoms may range from window not being
    #    brought to front ... to application crash with segmentation fault.」
    #   本程式就是 tkinter + onedir，正中警告；而且它也不吃「拖檔案到圖示上」。
    argv_emulation=False,
    target_arch=None,                # 跟著建置機器的架構走（見 README 的架構說明）
    codesign_identity=None,
    entitlements_file=None,
)

coll = COLLECT(                                                  # noqa: F821
    exe, a.binaries, a.datas,
    strip=False, upx=False, name=NAME,
)

if IS_MAC:
    # LSMinimumSystemVersion 是實測值，不是猜的：
    #   opencv-python-headless 4.14.0.94 的 wheel tag 是 macosx_14_0_x86_64
    #   與 macosx_13_0_arm64，`vtool -show-build cv2.abi3.so` 在 Intel 上讀到
    #   minos 14.0。**換 opencv 版本就要重量一次**（4.10.0.84 是 12.0 / 11.0）。
    MIN_OS = "13.0" if platform.machine() == "arm64" else "14.0"
    app = BUNDLE(                                                # noqa: F821
        coll,
        name=f"{NAME}.app",
        icon=None,
        bundle_identifier="com.oceanlabdesign.papertobim",
        info_plist={
            # 不設這個的話 Retina 上整個介面會被放大成模糊的點陣
            "NSHighResolutionCapable": True,
            # PyInstaller 不會自動加這一個。官方 spec-files 文件對它的說法是
            # 「necessary to allow macOS to render applications using retina resolution」
            "NSPrincipalClass": "NSApplication",
            "LSMinimumSystemVersion": MIN_OS,
            "CFBundleShortVersionString": "0.4.1",
            "CFBundleVersion": "0.4.1",
            "NSHumanReadableCopyright": "OceanLab Design",
        },
    )
