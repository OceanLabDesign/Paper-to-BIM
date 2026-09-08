# Paper-to-BIM Architecture & Roadmap

Paper-to-BIM 的目標是把舊建築圖面重建成**可追溯、可驗證、1:1 的正式 CAD / BIM 幾何**，而不是把 raster line 描成 vector line。

## Product Invariant

```text
Agent understands + chooses tools
        ↓
Observations / Evidence
        ↓
Constraints
        ↓
Deterministic Solver
        ↓
DrawingIR (mm, 1:1)
        ↓
DXF / IFC / BIM exporter
        ↓
Validation / Human Review
```

禁止的捷徑：

```text
image → trace pixels → CAD
LLM → invented coordinates → CAD
segmentation mask → DXF polygon
```

## Runtime Architecture

```text
Source PDF / Scan
      │
      ├─ Sheet / Tile Understanding
      │
      ▼
OpenRouter VLM Agent
      │
      ├─ Inspection Tools
      ├─ OCR / Reading Tools
      ├─ Semantic Vision Tools
      │      └─ Farside Vision API → GPU segmentation/detection
      ├─ Geometry Extraction Tools
      ├─ Constraint Tools
      └─ Solver Tools
             │
             ▼
          DrawingIR
          unit = mm
             │
      ┌──────┼──────┐
      ▼      ▼      ▼
     DXF    IFC    future BIM adapters
             │
             ▼
      Overlay / Closure / Conflict Review
```

## Responsibility Boundaries

### Agent

負責理解、選工具、建立 proposal、發現缺少的證據。

### Vision Tools

負責 pixel-space evidence，例如 mask、bbox、outline、line candidate。Vision result 不等於正式建築 geometry。

### Geometry / Constraint Solver

負責由尺寸、軸線、構件表、拓樸關係建立真實世界 mm geometry。Solver 不使用 LLM 執行數學求解。

### DrawingIR

唯一 canonical reconstruction representation。Exporter 只序列化 DrawingIR。

### Farside

外部 GPU capability provider。Paper-to-BIM 不管理 GPU，也不 import farside internals。

## Current ADR Chain

- [ADR-0012](../adr/0012-domain-architecture-reset.md) — Domain Architecture Reset
- [ADR-0013](../adr/0013-agent-tool-runtime-openrouter-byok.md) — Agent Runtime + OpenRouter BYOK
- [ADR-0014](../adr/0014-semantic-vision-tool-layer.md) — Semantic Vision Tool Layer
- [ADR-0015](../adr/0015-agent-evidence-workflow.md) — Agent Evidence Workflow
- [ADR-0016](../adr/0016-geometry-extraction-in-scale-reconstruction.md) — In-Scale Geometry Reconstruction
- [ADR-0017](../adr/0017-farside-vision-api-boundary.md) — Farside Vision API Boundary
- [ADR-0018](../adr/0018-first-floor-structural-vertical-slice.md) — First Real Vertical Slice

完整 ADR 索引見 [`docs/adr/README.md`](../adr/README.md)。

## First Production-Oriented Vertical Slice

第一個 benchmark 只做真實「壹層結構平面圖」：

```text
multi-page scan
→ tile / sheet placement
→ grid axes
→ dimensions
→ column tags / column evidence
→ segmentation where useful
→ constraints
→ solver
→ DrawingIR
→ 1:1 DXF
→ source overlay
→ conflict report
```

第一階段不追求完整牆、樑、板、門窗與 BIM。必須先證明 Grid + Dimension + Column 可以在真實舊圖上閉環。

## Roadmap

### R1 — Vision Provider Boundary

建立 `SegmentationProvider` 與 farside adapter，benchmark 可替換的 segmentation models。

### R2 — Evidence Tooling

補齊 sheet inspection、crop、OCR、mask-to-contour、line/rectangle fitting、tool audit。

### R3 — First-Floor Reconstruction

跑通軸線、尺寸鏈、柱與 1:1 DXF。

### R4 — Validation / Human Review

完成 source/reconstruction overlay、confidence、provenance、conflict review。

### R5 — Structural Geometry Expansion

依序加入 Wall → Beam → Stair → Slab / closed-face topology。

### R6 — Architectural / BIM Expansion

加入 Door / Window、多樓層一致性、level / height、IFC 與 BIM adapters。

## Definition of Done

Paper-to-BIM 的完成條件不是「圖看起來像」。正式 Entity 必須回答：

- 它是什麼？
- 真實尺寸是多少？
- 真實座標如何算出？
- 依據哪些原始圖面證據？
- Agent 使用過哪些工具？
- 是否存在 unresolved conflict？

只有能回答以上問題，才算 reconstruction，而不是比較昂貴的描圖。
