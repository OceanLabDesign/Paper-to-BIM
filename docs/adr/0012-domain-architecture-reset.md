---
number: 0012
title: Domain Architecture Reset — Evidence-Constrained Reconstruction
status: proposed
date: 2026-09-04
supersedes:
superseded_by:
---

# 0012. Domain Architecture Reset — Evidence-Constrained Reconstruction

## 脈絡

Paper-to-BIM 已經從單純的影像轉向量實驗，演進成一套「理解優先、尺寸約束、矛盾保留、可追溯」的舊圖重建流程。

ADR 0009、0010、0011 已經確立三個重要方向：

1. 不把像素拼接當成幾何真相。
2. 中樞先理解影像，CV 只量已指名的對象。
3. 跨片以語意錨點與尺寸鏈建立共同座標，而不是盲目 image registration。

目前主要問題已經不是 perception 演算法，而是 domain model 尚未正式分層。`plan_vN.yaml` 同時承擔 AI 判斷、幾何、衝突、不確定、覆寫與殘差處理；CSV 同時扮演 evidence store、pipeline checkpoint 與準資料庫。這在研究階段方便，但會阻礙後續擴展到門窗、多樓層、剖立面、BIM、人工校對與外部 Agent。

## 決定

採用 **Evidence-Constrained Reconstruction** 作為正式 domain architecture。

核心資料流：

```text
Source Image
    ↓
Observation
    ↓
Constraint
    ↓
Geometry Solver
    ↓
Entity
    ↓
DrawingIR
    ↓
Validation / Review
    ↓
Exporter
```

旁路資料：

```text
Provenance
Confidence
Conflict
ValidationResult
ReconstructionProposal
```

### 一、Plan 不再是模型

`plan_vN.yaml` 改定位為 `ReconstructionProposal`：它只代表某一輪 AI 對證據的提案，不是系統的 canonical geometry。

AI 可以：

- 建議 Observation 的語義類型；
- 建議 Observation 之間的關係；
- 建議 Constraint；
- 指出 Conflict / Uncertain；
- 要求額外量測或局部覆核。

AI 不可以：

- 直接成為最終座標來源；
- 直接寫 CAD；
- 靜默消解互相衝突的尺寸；
- 決定 pipeline 是否終止。

### 二、建立六個正式 Domain Object

#### Observation

代表「從來源圖面觀察到什麼」。Observation 是證據主張，不是真相。

例如：dimension text、axis symbol、wall stroke、column symbol、room label、material note。

#### Constraint

代表幾何或語義約束，例如：

- DISTANCE
- COINCIDENT
- PARALLEL
- PERPENDICULAR
- HORIZONTAL
- VERTICAL
- COLLINEAR
- CENTERED
- EQUAL
- OFFSET
- CLOSED_LOOP

Constraint 分為 hard / soft。直接尺寸標註通常為 hard；由圖面外觀推測的平行、置中、相等通常為 soft。

#### Entity

代表重建後的建築／製圖實體，例如 grid axis、wall、column、door、window、stair。

Entity 必須保留 provenance，且不得失去 uncertainty 狀態。

#### Conflict

矛盾是正式 domain object，不是例外。尺寸鏈不閉合、跨樓層不一致、來源互相衝突都可以合法存在於完成的 reconstruction result。

#### Provenance

所有最終 Entity 與 Constraint 都必須可反查：來源頁、來源區域、觀察 id、模型／演算法、人工修改紀錄。

#### DrawingIR

DrawingIR 是唯一 canonical reconstruction representation。CAD / IFC / Archicad / Revit exporter 只序列化 DrawingIR，不再直接消費 AI plan。

### 三、Observation ontology 與 Building Entity ontology 分離

現有 `core/classes.py` 將 wall、column、dim_line、dim_text、material_note、calc_note 混在同一個永久序列中。這三類概念應拆開：

```text
ObservationType
DrawingSymbolType
EntityType
```

新 domain identity 使用穩定字串，例如：

```text
building.column
building.wall
drawing.grid_axis
annotation.dimension_text
annotation.material_note
```

現有數字 class id 僅保留為 legacy compatibility，不再作為未來 domain identity。

### 四、CSV 降級為 Projection / Artifact

既有 CSV 不刪除，因為它們對除錯、人工檢查、回歸測試仍有價值。

但 CSV 不再被視為 domain source of truth。

對應關係：

| 現有產物 | 新角色 |
|---|---|
| `03_lines.csv` | Observation projection |
| `03_texts.csv` | Observation projection |
| `03_detections.csv` | Hypothesis / Observation projection |
| `03_elements.csv` | EntityCandidate projection |
| `04_readings.csv` | Measurement Observation projection |
| `05_chains.csv` | Constraint projection |
| `plan_vN.yaml` | ReconstructionProposal |
| `08_conflicts.csv` | Conflict projection |
| `07_walls.csv` | DrawingIR projection |
| `07_columns.csv` | DrawingIR projection |
| `residuals_vN.csv` | ValidationResult projection |
| DXF | Export Artifact |

### 五、Solver 從 perception 分離

`perception/s05_solve.py` 的責任不是 perception，而是 constraint solving。

逐步遷移至：

```text
solver/
  dimension_solver.py
  coordinate_solver.py
  topology_solver.py
  constraint_solver.py
```

舊入口在過渡期保留 adapter，避免一次破壞整條 pipeline。

### 六、Exporter 改吃 DrawingIR

現行 exporter registry 與「MCP 不得成為 exporter dependency」的決策保留。

目標介面：

```text
DrawingIR → DXF
DrawingIR → IFC
DrawingIR → Archicad
DrawingIR → Revit
DrawingIR → Rhino
```

過渡期允許 legacy plan adapter：

```text
plan_vN → legacy adapter → DrawingIR → exporter
```

新 exporter 不得直接依賴 AI plan schema。

### 七、流程控制仍由 deterministic orchestrator 掌握

ADR 0012 不推翻既有鐵則：

- iteration 次數由程式控制；
- termination condition 由程式判斷；
- validation failure 不由模型自行忽略；
- 同一 DrawingIR 重複 export 必須得到相同幾何。

### 八、ADR / Schema / Code 的責任分離

為避免同一規則在 ADR、comment、config、CSV schema 出現互相衝突版本，新增規則：

> ADR 解釋 why；Schema 定義 what；Code 實作 how。可執行數值規則只能有一個 source of truth。

文件中的實測數值只能作為 evidence，不得被下游程式直接解析為設定值。

## 套件方向

新的目標結構：

```text
domain/
  observation.py
  constraint.py
  entity.py
  conflict.py
  provenance.py
  drawing_ir.py

ingestion/
understanding/
measurement/
solver/
reconstruction/
validation/
exporters/
adapters/
  llm/
  mcp/
  slate/
artifacts/
orchestration/
```

本 ADR 不要求一次完成目錄搬移。採逐段 strangler migration，先建立 domain，再讓舊 pipeline 逐步改成產生／消費 domain object。

## 第一條 Vertical Slice

重整後第一個正式閉環只做：

```text
一張平面圖局部
→ Vision understanding
→ 3–4 條 grid axis
→ dimension observations
→ dimension constraints
→ constraint solver
→ 2–4 個 column entities
→ DrawingIR
→ DXF
→ overlay validation
```

不在這個 vertical slice 加牆、門窗、樓梯、完整 BIM。

## Acceptance Criteria

1. `domain` package 不依賴 LLM provider、OpenCV、ezdxf 或 MCP。
2. Observation / Constraint / Entity / Conflict / Provenance / DrawingIR 有穩定 schema。
3. DrawingIR 可 JSON round-trip。
4. 每個 Entity 可以追溯 provenance。
5. Constraint 可以標記 hard / soft 與 confidence。
6. Conflict 可以在 reconstruction 完成時仍保持 unresolved。
7. 新 exporter 介面以 DrawingIR 為輸入。
8. legacy pipeline 可以透過 adapter 漸進遷移，不要求一次改完。
9. 相同 DrawingIR 重複 export 必須 deterministic。
10. ADR 0010、0011 的理解優先與拼座標不拼像素原則保持有效。

## 與既有 ADR 的關係

保留並延續：

- ADR 0004 證據 id 命名空間
- ADR 0005 LLM 供應商薄介面
- ADR 0006 技能格式
- ADR 0007 匯出器不得相依 MCP
- ADR 0008 輸入格式
- ADR 0009 理解而非拼圖
- ADR 0010 理解優先
- ADR 0011 拼座標不拼像素

本 ADR 是 umbrella architecture reset，不抹除過去失敗記錄。過往 ADR 中已被新 domain model 取代的 pipeline-level schema，後續逐份標記 superseded / implementation-detail。

## 後果

正面：

- AI 模型、solver、exporter 可以獨立替換；
- 幾何真相不再藏在 AI plan；
- provenance 與 conflict 成為一等資料；
- 後續可自然延伸到多樓層、剖立面與 BIM；
- Slate / MCP 可以作 adapter，不污染核心。

代價：

- 短期會同時存在 legacy CSV/plan 與新 domain object；
- 需要 adapter 與 migration tests；
- 部分既有模組名稱與 stage number 將逐步失去架構意義。

這些代價可接受，因為目前仍處於 skeleton / prototype 階段，尚未累積大量 production data。現在進行 domain reset 的遷移成本遠低於系統正式投入案件後再處理。
