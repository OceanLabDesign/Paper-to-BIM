# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## 工作準則（先於本檔其餘所有內容）

你是一位遵循 KISS、YAGNI、最小差異（minimal diff）與範圍紀律（scope discipline）的資深軟體工程師。請先理解任務、相關程式碼與現有測試，辨識完成需求不可或缺的行為與驗收（validation）條件（acceptance criteria），再採用能完整通過驗收的最小可行方案。

決策優先順序如下：

1. 正確性與安全性。
2. 滿足明確需求與驗收條件。
3. 維持範圍外的既有行為與公開介面。
4. 沿用現有架構、程式風格、模組與相依套件。
5. 將修改限制在最少的檔案與程式碼。
6. 僅在目前需求明確需要時考慮額外擴充性。

局部問題請採用局部修正。新增抽象層、設計模式、共用元件、設定項、資料表、API、相依套件或大規模重構時，必須能直接對應到本次需求；若沒有直接關聯，請沿用現況。測試聚焦於本次變更的核心行為、合理邊界情境（edge case）與實際回歸風險。

遇到歧義時，優先採用最簡單、可逆且符合現有慣例的解讀。只有當不同選擇會實質影響公開介面、資料結構、安全性或核心行為時，才提出澄清問題。

驗收條件通過後即停止擴張範圍。額外的重構、清理與未來優化請列為可選建議，不納入本次實作。完成前請審查 diff，確認每項變更都能追溯到明確需求，並移除投機性抽象（speculative generality）、預先設計的擴充點與無關修改。

最小方案仍須保持正確、安全、清楚、可維護，並具備符合目前風險的錯誤處理。最終回報僅包含實作摘要、修改檔案、驗證結果、必要假設與已知限制。

> 這條準則與本專案的既有紀律同向：規格 §0.1「一次實作一個檔案」、§0.4「與文件衝突就停下來問」、
> §12 的禁止清單，本質上都是同一件事 —— **不要做現在還不需要的東西**。
> 兩者衝突時以規格為準，因為規格是這個專案的驗收條件本身。

## 專案現況

- 這個 repo 目前是**規格書＋骨架（skeleton）**：`docs/程式設計_v0.4.md`（v0.4.1） 是規格，其餘 Python 檔幾乎全是 stub（呼叫即 `NotImplementedError`，附規格段落）。沒有套件設定、不是 git repo。
- 已經是**實作**而非 stub 的只有四處：`core/config.py`（§10 實測參數逐字轉錄）、`core/case.py`（§3 路徑）、`core/io.py`（§1.1 的 `final()`）、`planning/orchestrator.py` 的迴圈骨架（§5）。動這四處等於動規格。
- 規格的矛盾（conflict）與缺漏收在本機的 `待決事項.md`（**不進版控**）。開工前先看那份；沒有那個檔就先問負責人（owner），不要自行取捨。
- 那份規格書是實作的唯一依據，本檔只是它的導航與速查。**輸入輸出照規格走，不要自行發明格式；任何與規格衝突的實作決定 → 停下來問，不要自行取捨**（規格 §0）。
- **v0.4.1 起規格自足**，不再依賴《架構文件 v0.3》——`io.final()` 與「三源（three sources）」的定義已補進 §1.1／§1.2。仍有 v0.3 才有的細節（既有 CSV 欄位全清單）需要時向負責人索取，不要憑空補。
- 本機的裁決（ruling）文件（**不進版控**）優先於規格書，其內容已折進 v0.4.1。
- 建造順序見規格 §11，目前停在**第 1 步：負責人手寫契約（contract）三件套**。契約未落地前，s01 以後的模組不該開工。

## 指令

```bash
python3 tests/smoke.py                          # 骨架煙霧測試：32 支模組 import + §10 參數比對 + §11 進度
python3 -m planning.orchestrator cases/<案號_地段>       # 全迴圈入口（目前跑到第一個 stub 就停）
```

除此之外**尚未建立 build / lint / test 工具鏈**（無 pyproject.toml、requirements.txt、CI）。從 repo root 執行即可。要不要正式打包等第一支模組落地再定，不要假設已經存在。

### 相依：照 §11 建造順序分階段裝，不要一次全裝

`tests/smoke.py` 只需要 **Python 3.10–3.14**（上下限來自 IfcOpenShell 與 rhino3dm）。PyYAML 選用，沒有的話 `[5]` 自動跳過。

| 步 | 模組 | 套件 |
|---|---|---|
| 2 | `s01_ingest` | PyMuPDF |
| 3 | `s01b` / `s02b` / `s03_lines` | OpenCV、NumPy |
| 3 | `s03_texts` | PaddleOCR-VL（很重，帶 PaddlePaddle，可延後） |
| 5 | `s07_execute` / `export_review` | ezdxf、openpyxl |
| 8 | `ifc` 匯出器（exporter） | IfcOpenShell |
| — | `rhino` 匯出器 | rhino3dm |

**動手前先查現況**，不要照這張表盲裝：

```bash
python3 -c "
for m in ['yaml','fitz','cv2','numpy','ezdxf','ifcopenshell','rhino3dm','openpyxl']:
    try: __import__(m); print('  ✓', m)
    except ImportError: print('  ✗', m)"
```

中樞（LLM）：雲端設 `ANTHROPIC_API_KEY` / `OPENAI_API_KEY`，本地用 Ollama / vLLM / LM Studio（同一支 `openai_compat` 轉接器（adapter））。**金鑰走環境變數，不要寫進 `core/config.py`** —— 那支會進版控。

**外部 CAD 軟體一律不是必要的。** DXF 與 IFC 都是純檔案輸出。ArchiCAD / Revit / VisualARQ 只在要產「該軟體裡可編輯的原生牆」時才需要，各自的硬相依（hard dependency）與 OS 限制見規格 §8.1 與 `execution/exporters/` 各支的 docstring。以上**全部不需要 API token**。

測資（test data）固定用 68 年案；每支模組自帶自測（規格 §13）。`403+403=806`（尺寸鏈（dimension chain）閉合（closure））是第一筆迴歸測試（regression test）。

## 架構：兩層＋一個迴圈

```
被動層（視神經，確定性，一次跑完）
  s01 拆片 → s01b 方向 → s02 版面(VLM 一次) → s02b 品質地圖
  → s03 線段/偵測/富標籤 → s04 三源讀取 → s05 尺寸鏈
迴圈（≤3 輪，控制權在 planning/orchestrator.py）
  s06 中樞(LLM) → plans/plan_vN.yaml
  s06v validate(純程式碼) → 未引證據就退件
  s07 execute → out/*.dxf
  s08 compare → residuals_vN.csv → 回饋給中樞
s09 跨樓層檢查 → Excel 校對 → 人
```

需要跨檔案才看得出來的幾條結構性約束：

- **控制權在程式碼，不在 agent。** `for` 迴圈、終止條件（`residuals_all_handled` 由程式判定，不是 agent 自稱）、退件（rejection）重寫（同輪一次為限）全在 `planning/orchestrator.py`；中樞（planning）永遠只被呼叫。這是全系統唯一允許的 orchestrator，其餘每一步仍可單獨執行。
- **腦手分離。** 中樞只產 plan YAML，不准寫 CSV、不准碰 ezdxf。`s07_execute` **只讀 plan，不讀任何 03/04 檔**——這是腦手分離的實作保證，破了它整個設計就失效。
- **驗收是純程式碼的閘門（gate）**（規格 §6.2，六條退件規則）。重點兩條：任一 judgment 的 `evidence` 不得為空且 id 必須真的存在於 CSV；幾何座標必須追溯得到 chain 或 measure 來源（**禁止目測座標（eyeballed coordinates）**）。v2 起上一輪每條殘差（residual）都要出現在 `residual_handling`，動作只有 `revise` 或 `report`。
- **脈絡（context）節食（context diet）。** 中樞收到的是摘要（sheets 該列、品質地圖（quality map）差區、排除帶（exclusion zone）、全部 chains、elements 統計＋高信心清單），細節靠主動工具箱自己去看（`crop_look` / `redetect` / `read_number` / `measure` / `trace` / `compare_floors`）。**不要把 649 條原始線段（line segment）塞進脈絡。**
- **富標籤（rich label）是主張不是事實。** `03_detections` / `03_elements` 帶 `evidence, provenance, quality_zone, status`；`status` 生命週期 `proposed` →（中樞在 plan 裡裁定（adjudication））`adopted / rejected / uncertain`，由 orchestrator 在 s07 之前回寫（write back）。中樞可推翻標籤，但 `overrides` 必附 `reason`。
- **兩個 sub-agent 只給建議**（讀數（reading）仲裁（reading arbitration）、殘差偵探（residual detective））。產出只能進 plan 的 `uncertain` / `judgments` 並經過驗收，**不得直接寫任何 CSV**。
- **矛盾是產出，不是障礙。** 對不起來的寫進 plan 的 `conflicts`，不准為了收斂挑一邊蓋掉另一邊；「帶著矛盾收工」是成功。
- **不確定往上傳不往下傳。** 一個案子一個資（personal data）料夾、每步讀檔寫檔、編號即順序；CSV 為主（幾何用 WKT 欄位）、程式用 `dict` 不用 dataclass；讀值一律走 `io.final()`。案件資料夾結構見規格 §3，`plans/` 是中樞的思考史（plan_v1 → residuals_v1 → plan_v2 …）。

## 契約三件套（只能引用，不能改）

`core/fields.py`（CSV 欄位）、`core/classes.py`（15 類偵測類別（detection class），**順序即 id，永不重排**）、`core/plan_schema.py`（plan 結構＋驗收規則）由負責人親手寫。欄位引 `fields.py`、類別引 `classes.py`，不要在模組裡另立一套名字。

## 實測校準參數（`core/config.py`，68 年案驗證通過，不要「順手優化」）

- `PX_PER_CM = DPI / 2.54 / SCALE ≈ 1.181`（DPI 300、1:100、單位 cm）；牆 24cm ≈ 28px、總寬 806cm ≈ 952px。
- `ADAPTIVE_BLOCK, ADAPTIVE_C = 31, 12` — **禁用 Otsu**，這組才在曬圖陰影下活下來。
- `HOUGH_THRESHOLD, MIN_LINE_LENGTH, MAX_LINE_GAP = 60, 60, 6`；`WALL_GAP_PX = (12, 42)`。
- `MAX_ITER = 3`。68 年案第 1 頁實測方向是 **180°**。
- `ASSUMED` 是暫用值（層高（floor-to-floor height） 1F 400／其他 320、牆厚外 24／內 12、板厚 15）。**由它導出的任何值：`thickness_src="assumed"`、信心 ≤ 0.4、輸出檔名帶 `_draft`** —— 粗胚 BIM（draft BIM） 被誤當精確模型是 v0.3 風險表（risk register）上的中度風險。68 年案 A-2 頁的立面圖（elevation view）有標高（elevation），量一次即可換成真值。

## 目錄結構

```
core/        契約與設定。fields/classes/plan_schema 是 ★ 契約三件套（負責人手寫，只能引用，
             目前刻意留空 → import 會 ImportError，那是預期行為，不要用預設值繞過）；
             config.py=§10 實測參數＋ASSUMED；case.py=§3 路徑（全 repo 唯一該出現 CSV
             檔名的地方）；io.py=§1.1 的 final()（verified_value 優先，皆空回 None）
perception/  看：s01–s05（確定性，一次跑完）＋ run_passive.py ＋ detectors/{rule,yolo}
planning/    判斷：orchestrator（唯一流程控制器）、proposer／fake_proposer（s06）、validate（s06v）、
             context（§7.1 節食）、tools（§7.2 工具箱＋TOOL_SPECS）、prompts（§7.3 逐字）、
             subagents/、llm/（供應商介面：anthropic 原生＋openai_compat 涵蓋
             OpenAI/Ollama/vLLM/LM Studio）、skills/（SKILL.md 按需載入＋選用 run.py）
execution/   畫：s07_execute（只讀 plan，委派給 exporters）、s08_compare、
             exporters/（dxf 為 MVP；rhino/visualarq/archicad/revit 預留；ifc 被 §12 擋著）
review/      校對：s09_crosscheck、export_review（Excel，conflicts 去重只在這裡做）
cases/       _template/ 案件資料夾範本（§3 骨架＋說明；複製後改名為 <案號_地段>）
examples/    plan_vN.sample.yaml（§6.1 格式範例，id 是假的、非真實測資；§13 自測樣本另備）
```

套件用架構通用詞（perception → planning → execution），中文比喻留在 docstring 與規格書：看 → 判斷 → 畫 → `review/` 校對（review）。

中樞的函式叫 `propose_plan()`（模組 `planning/proposer.py`／`fake_proposer.py`）—— 名字講的是**產出**，不是它由什麼做的。英文 `brain` 一詞已退出 repo，概念一律用「中樞」。模組檔名一律照 §8 的 sXX 原名。

## 文件與 commit 的語言慣例

**一律中文**，不做中英對照版（雙語文件的維護成本會讓其中一份必然過時）。
但**專有名詞第一次在該文件出現時，於其後加括號標註英文原文**：

```
架構決策紀錄（Architecture Decision Record, ADR）
自適應二值化（adaptive thresholding）
曬圖（diazo print）
```

同一份文件裡同一個詞**只標第一次**，之後直接用中文 —— 每次都標會讓文章讀不下去。
對應表見 [`docs/術語對照.md`](docs/術語對照.md)（175 筆，其中 17 筆標⚠沒把握、
**不要寫進文件**）。**不要自己另譯**；表裡沒有的詞，加進表再用。

**commit 訊息同一套規則**：中文，專有名詞加括號原文。

⚠ **逐字轉錄的區塊不准加註**：規格 §5 的迴圈 code block、§7.3 的 system prompt、
§10 的參數區塊、§6.1 的 plan 範例 —— 這些是逐字轉錄，加了括號就不再逐字。
`tests/smoke.py` 的 `[9]` 會擋。

## ⚠ 引用規格前先 grep

**這個失誤已經發生兩次**，兩次都是把自己寫進 docstring 的話，
之後當成規格條文引用，並據此擋掉一個其實可行的方向：

| 捏造的引用 | 規格實際只寫了 |
|---|---|
| §2「s09 比對柱位、牆線、開口」 | 「s09 跨樓層檢查」六個字 |
| §8「不要做特徵點拼接」 | 「不用重新對位」—— 是「不用」，不是「不准」 |

**寫「規格 §N 說…」之前，先 `grep` 規格書確認那句話真的在裡面。**
自己補的推論要標成推論（例如「代擬」「本檔判斷」），不要寫成引用。

這件事的代價不是文件不精確，是**用一條不存在的禁令否決掉可行的設計**。

## 架構決策紀錄（Architecture Decision Record, ADR）

`docs/adr/` 記的是**已決的架構決定＋當初放棄了什麼**。方法與模板見 `docs/adr/README.md`。

這條流水線的三段不要混：

```
待決事項.md          撞到歧義 → 停下來問（§0.4）      本機，不進版控
待決事項_裁決.md      裁決那一刻                       本機，不進版控
docs/adr/NNNN-*.md   已決 ＋ 理由 ＋ 放棄了什麼        進版控，只寫技術理由
```

**什麼時候寫**：四個條件同時成立 —— 真的有替代方案、改起來會痛（動到公開介面／
資料結構／契約）、影響超過一個檔案、半年後看程式碼看不出為什麼。
**修 bug、改名、加測試、規格已寫死照抄的，不要寫。** ADR 不是會議紀錄，寫太多等於沒寫。

編號**永不重用、永不重編**；被取代的 ADR **不刪不改內容**，只改 `status: superseded`
並填 `superseded_by`。`tests/smoke.py` 的 `[8]` 會查前置資料（front matter）、編號、必要段落與索引。

## 工作方式

- **一次實作一個檔案。** 派工格式（規格 §13）：引契約、指段落、定 I/O、禁副作用（side effect）、附測資。
- 中樞相關程式（§5–§7）**先做骨架與假中樞（回固定計畫）**，整個迴圈跑通、DXF 在 ArchiCAD 打得開之後，才接真 LLM。第 5 步先於第 6 步是刻意的：真中樞（real proposer）接上時只剩一個變因。
- 現在**不要做**：把迴圈控制交給 agent（含讓中樞自己決定要不要再跑一輪）、YOLO（等存量配對盤點數字）、IFC exporter（等 ArchiCAD 四道牆往返測試（round-trip test）通過）。MVP 輸出 **DXF 優先**。
- 一開始不上資料庫、不做網頁校對（Excel 先頂）、不追求全自動。
