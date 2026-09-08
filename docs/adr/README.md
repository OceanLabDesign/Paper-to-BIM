# 架構決策紀錄（ADR）

## 這是什麼

一個決策一個檔。記的不是「我們做了什麼」（程式碼自己會說），而是
**「當時有哪些選項、為什麼選這個、放棄了什麼」** —— 那是程式碼永遠留不住的部分。

半年後有人（包括未來的 Claude Code）想改某個決定時，ADR 讓他知道
**這個決定當初擋掉了什麼**，而不是把踩過的坑再踩一次。

## 與現有兩份文件的關係

```text
待決事項.md          撞到歧義 → 停下來問（規格 §0.4）
      ↓ 負責人裁決
待決事項_裁決.md      裁決那一刻的紀錄
      ↓ 折進規格與程式
docs/adr/NNNN-*.md   已決 ＋ 理由 ＋ 放棄了什麼
```

前兩份**留在本機不進版控**（含業務判斷與內部溝通）；ADR 進版控，只寫**技術理由**。同一件事在兩邊都出現時，ADR 是可以對外看的那個版本。

## 什麼時候要寫

四個條件**同時**成立才寫。ADR 不是會議紀錄，寫太多等於沒寫：

1. **真的有替代方案**，而且不只一個聽起來合理
2. **改起來會痛** —— 動到公開介面、資料結構、契約（contract），或已有資料引用
3. **影響超過一個檔案**
4. **半年後的人看程式碼看不出為什麼**

反例：修 bug、改變數名、加一個測試、規格已經寫死照抄的東西。

## 怎麼寫

複製 `TEMPLATE.md`，編號取目前最大號 +1（**永不重用、永不重編**）。一份 ADR 應該一頁看完；寫不完通常代表它其實是兩個決定。

## 狀態

| 狀態 | 意思 |
|---|---|
| `proposed` | 已寫但還沒拍板 |
| `accepted` | 已定案並落地 |
| `superseded` | 被後來的 ADR 取代，不刪內容，只更新狀態與 `superseded_by` |
| `rejected` | 認真考慮過但沒採用，保留避免重複討論 |

## 索引

| # | 標題 | 狀態 |
|---|---|---|
| [0001](0001-三段式套件命名.md) | 三段式套件命名與中樞（planning）的函式名 | accepted |
| [0002](0002-契約三件套改為代擬審核.md) | 契約三件套改為「代擬＋審核」 | accepted |
| [0003](0003-十五類偵測類別.md) | 15 類偵測類別（detection class）與「順序即 id」 | accepted |
| [0004](0004-證據id命名空間.md) | 證據 id 命名空間（namespace） `EVIDENCE_NS` | accepted |
| [0005](0005-llm供應商薄介面.md) | LLM provider 薄介面 | accepted |
| [0006](0006-技能格式.md) | 技能（skill）＝指令包＋選用的可執行腳本 | accepted |
| [0007](0007-匯出器不得相依mcp.md) | 匯出器不得相依 MCP | accepted |
| [0008](0008-輸入格式.md) | 散開的掃描影像如何進入座標系 | superseded by 0009 |
| [0009](0009-理解而非拼圖.md) | 理解而非拼圖 | proposed |
| [0010](0010-理解優先.md) | 理解優先 | proposed |
| [0011](0011-拼座標不拼像素.md) | 補上度量（metric）層：拼座標不拼像素 | proposed |
| [0012](0012-domain-architecture-reset.md) | Domain Architecture Reset — Evidence-Constrained Reconstruction | proposed |
| [0013](0013-agent-tool-runtime-openrouter-byok.md) | Agent Tool Runtime + OpenRouter BYOK Model Provider | proposed |
| [0014](0014-semantic-vision-tool-layer.md) | Semantic Vision Tool Layer 與 Segmentation Provider | proposed |
| [0015](0015-agent-evidence-workflow.md) | Agent Evidence Workflow 與工具使用邊界 | proposed |
| [0016](0016-geometry-extraction-in-scale-reconstruction.md) | Geometry Extraction 與 In-Scale Reconstruction | proposed |
| [0017](0017-farside-vision-api-boundary.md) | Farside Vision API 整合邊界 | proposed |
| [0018](0018-first-floor-structural-vertical-slice.md) | 壹層結構平面圖 Vertical Slice 與 Benchmark | proposed |

## 目前的主架構鏈

```text
0012 Domain Architecture Reset
  ↓
0013 Agent Runtime / OpenRouter BYOK
  ├─ 0014 Semantic Vision Tool Layer
  ├─ 0015 Agent Evidence Workflow
  ├─ 0016 In-Scale Geometry Reconstruction
  ├─ 0017 Farside Vision API Boundary
  └─ 0018 First Real Vertical Slice
```

0014–0018 是同一個 roadmap 的不同決策邊界，不應再合併成單一大型 ADR。
