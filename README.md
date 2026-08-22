# Paper-to-BIM

把民國 68 年（1979）的建照掃描圖，重建成可用的 BIM 模型。

老圖是曬圖，有摺痕、陰影、暈開的筆畫。人可以看懂，程式不行 ——
這個專案處理的就是「看不清楚」這件事本身。

> **現況：骨架階段。** 模組多數是 stub，契約三件套是待審核的草案。
> 尚未跑過任何真實案件。

## 這個專案的主張

多數「AI 自動化」的作法是讓模型從頭包到尾。這裡刻意不那樣做：

**控制權在程式碼，不在 agent。** 迴圈次數、終止條件、退件重寫，全寫死在
`planning/orchestrator.py` 裡。中樞（LLM）只被呼叫，它不能決定要不要再跑一輪。

**腦手分離。** 中樞的產出是一份**繪圖計畫**（YAML），不是動作。
執行那一層只讀計畫、不讀原始偵測資料 —— 中樞說不清楚的東西，畫不出來。

**矛盾是產出，不是障礙。** 尺寸鏈加總對不上、樓層之間柱位對不齊 ——
這些寫進 `08_conflicts.csv`，不准挑一邊蓋掉另一邊。**帶著矛盾收工是成功。**

**不確定往上傳，不往下傳。** 讀數三個來源不一致就標紅送人工，
不會偷偷選一個看起來合理的。值未定就是未定，不准往下游傳。

最後一條是有代價的：這套系統**不追求全自動**，它追求的是
「哪裡不確定，你一眼看得到」。

## 架構

```
掃描 PDF
  ↓ perception ── 視神經，確定性，一次跑完
  拆片 → 轉正 → 版面 → 品質地圖 → 線段 → 偵測 → 文字 → 富標籤 → 三源讀取 → 尺寸鏈
  ↓
┌─ planning ── 迴圈，控制權在 orchestrator，最多 3 輪 ─────────┐
│  中樞（LLM）產出 plan_vN.yaml                                │
│  驗收（純程式碼）：沒引證據就退件                              │
│  execution：照計畫確定性執行 → DXF                            │
│  對照：像素重疊算術 → 殘差 ──回饋──→ 中樞                      │
└──────── 終止＝「殘差皆已修或已報告」，由程式碼判定 ────────────┘
  ↓
跨樓層檢查 → Excel 校對 → 人
```

| 套件 | 角色 | 內容 |
|---|---|---|
| `core/` | 契約 | 欄位、類別、計畫結構、實測校準參數 |
| `perception/` | 看 | s01–s05，確定性，不迴圈 |
| `planning/` | 判斷 | orchestrator、中樞、驗收、工具箱、技能、LLM 供應商層 |
| `execution/` | 畫 | DXF／IFC／ArchiCAD／Revit／Rhino／VisualARQ 匯出器 |
| `review/` | 校對 | 跨樓層檢查、Excel 匯出 |

## 需要先裝什麼

**短答：現在什麼都不用裝。** 骨架健檢只要 Python 3.10+（建議 3.12）。

相依刻意**照規格 §11 的建造順序分階段裝** —— 一次全裝會裝一堆還用不到的東西，
而且 PaddleOCR 那類套件很重。目前尚未建立 `requirements.txt`，用得到再裝。

### 第 0 步｜現在

| | |
|---|---|
| **Python 3.10–3.14** | 上下限來自 IfcOpenShell 與 rhino3dm 的支援範圍 |
| PyYAML | 選用。沒有的話 `smoke.py` 的 `[5]` 會自動跳過 |

### 依建造順序

| 步 | 模組 | 需要 | 說明 |
|---|---|---|---|
| 2 | `s01_ingest` | **PyMuPDF** | 讀 PDF 影像 XObject 的放置矩陣 |
| 3 | `s01b`／`s02b`／`s03_lines` | **OpenCV**、**NumPy** | 自適應二值化、霍夫轉換 |
| 3 | `s03_texts` | **PaddleOCR-VL** | 很重，會帶 PaddlePaddle。可延後到真的要跑文字時 |
| 5 | `s07_execute` | **ezdxf** | DXF 輸出，MVP 的唯一落地路徑 |
| 5 | `export_review` | **openpyxl** | Excel 校對介面 |
| 6 | 中樞 | 見下方 LLM 一節 | |
| 8 | `ifc` 匯出器 | **IfcOpenShell** | 純檔案，不需任何 CAD 軟體 |
| — | `rhino` 匯出器 | **rhino3dm** | 純檔案，不需 Rhino |

```bash
pip3 install pymupdf opencv-python numpy openpyxl   # 第 2–3 步
pip3 install ezdxf                                   # 第 5 步
pip3 install ifcopenshell rhino3dm                   # 需要時
```

### 中樞（LLM）—— 雲端或本地二選一

| | |
|---|---|
| 雲端 | 設 `ANTHROPIC_API_KEY` 或 `OPENAI_API_KEY`。不必裝任何東西 |
| 本地 | **Ollama**／**vLLM**／**LM Studio** 擇一，走同一支 OpenAI 相容轉接器 |

本地部署不只是省錢：掃描圖含個資與著作權，**跑本地模型時圖不出機器**。

### 外部應用程式 —— 只有想要「原生 BIM 物件」時才需要

DXF 與 IFC 都是純檔案輸出，**不需要安裝任何 CAD 軟體**。
以下只在你要把成果變成該軟體裡可編輯的牆／柱時才需要：

| 目標 | 需要 | 註 |
|---|---|---|
| 驗 IFC | **Blender 4.2+ 與 Bonsai** | 免費。建議先用它驗，不必動用商業授權 |
| ArchiCAD | ArchiCAD 25–29 執行中 ＋ 授權 ＋ **Tapir Add-On ≥ 1.5.7** | Tapir 是硬相依：官方 API 建不了牆 |
| Revit | **Windows** ＋ Revit 完整版 ＋ **pyRevit ≥ 6.5.4** | Revit LT 沒有 API，整條路不成立 |
| VisualARQ | **Windows** ＋ Rhino 8 ＋ VisualARQ 3 商業授權 | 官方逐字「It only works on Windows.」 |

以上**全部不需要 API token**。唯一真的需要憑證的是 Autodesk Platform Services
（雲端 Revit），本專案不實作。細節見規格 §8.1。

### 檢查現在缺什麼

```bash
python3 -c "
for m in ['yaml','fitz','cv2','numpy','ezdxf','ifcopenshell','rhino3dm','openpyxl']:
    try: __import__(m); print('  ✓', m)
    except ImportError: print('  ✗', m)"
```

## 開始

```bash
python3 tests/smoke.py                      # 骨架健檢：模組、契約、測資、逐字區塊
python3 -m planning.orchestrator cases/<案號_地段>   # 全迴圈入口（目前跑到第一個 stub 就停）
```

從 repo 根目錄執行即可，尚未建立套件打包。

## 文件

| | |
|---|---|
| [`docs/程式設計_v0.4.md`](docs/程式設計_v0.4.md) | 規格書。唯一依據，實作與它衝突時以它為準 |
| [`docs/adr/`](docs/adr/) | 架構決策紀錄 —— 當初有哪些選項、為什麼選這個、放棄了什麼 |
| [`CLAUDE.md`](CLAUDE.md) | 給 Claude Code 的工作準則與導航 |
| [`cases/_template/`](cases/_template/) | 案件資料夾範本 |

案件資料（掃描圖、中間產物、輸出）**不進版控** —— 原始 PDF 可能含個資與著作權，
其餘都能從原始 PDF 重生。

## 校準

參數是實測出來的，不是調出來的。以 1:100、300dpi 為例：

```
1 cm ≈ 1.181 px      24cm 牆 ≈ 28px      806cm 總寬 ≈ 952px
自適應二值化 (31, 12)  ← 禁用 Otsu，這組才在曬圖陰影下活得下來
```

## 授權

Apache License 2.0
