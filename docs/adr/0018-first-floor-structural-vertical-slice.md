---
number: 0018
title: 壹層結構平面圖 Vertical Slice 與 Benchmark
status: proposed
date: 2026-09-08
supersedes:
superseded_by:
---

# 0018. 壹層結構平面圖 Vertical Slice 與 Benchmark

## 脈絡

Paper-to-BIM 已完成 domain reset、Agent runtime、OpenRouter BYOK 與第一個 dimension/grid solver 的骨架。下一階段不得再以人工生成 demo 圖作為主要驗證，必須使用真實舊建築調案圖建立完整 reconstruction vertical slice。

本輪對話使用的 58 頁掃描調案圖中，第 34 頁為適合的壹層結構平面圖 benchmark，包含柱、樑、板、RC wall 等結構資訊，足以暴露真實掃描、跨頁、文字與幾何辨識問題。

## 決定

第一個正式 benchmark scope：

```text
壹層結構平面圖
```

第一階段 Entity 僅包含：

```text
Grid Axis
Dimension
Column
```

暫不要求：

```text
Beam
Slab
Door
Window
Full BIM
```

## Pipeline

```text
PDF
↓
Sheet / Tile discovery
↓
Semantic placement / shared drawing coordinates
↓
Agent inspection
↓
Axis observations
↓
Dimension observations
↓
Column observations
↓
Vision segmentation / outline evidence
↓
Constraint generation
↓
Geometry solver
↓
DrawingIR (mm)
↓
DXF 1:1
↓
Overlay validation
↓
Human review / conflict report
```

## 拼圖原則

延續 ADR-0011：拼座標，不拼像素。

Tile placement 可以使用圖框、軸線、尺寸鏈、重疊內容等 semantic anchors。系統不要求先建立完美 stitched raster 才能重建幾何。

## Benchmark Dataset Requirements

至少包含：

- 真實掃描；
- 多 tile / 分頁；
- 低解析度或模糊區域；
- 軸線；
- 尺寸鏈與總尺寸；
- 柱編號；
- 柱尺寸／配筋表可交叉引用；
- 部分難讀文字；
- 可人工建立 ground truth 的局部區域。

## Metrics

### Recognition

```text
axis recall / precision
dimension read accuracy
column detection recall / precision
column tag association accuracy
```

### Geometry

```text
dimension closure error
axis coordinate error (mm)
column center error (mm)
column size error (mm)
```

### Reconstruction

```text
DrawingIR completeness
unresolved conflict count
human corrections per sheet
provenance completeness
```

### Runtime / Cost

```text
LLM calls
GPU calls
GPU seconds
CPU processing time
total latency
provider/model usage cost
```

## Completion Definition

Vertical Slice 成功不是「畫面看起來差不多」。必須：

1. 自動找到主要軸線；
2. 自動讀取主要尺寸鏈；
3. 由 solver 求得 mm 座標；
4. 建立柱 Entity；
5. 匯出 1:1 DXF；
6. 可 overlay 原始掃描做視覺檢查；
7. 每個 Entity 可追溯到 Evidence / ToolCall / Source Region；
8. 所有未解矛盾可列出；
9. 不靠人工逐線描 CAD 才能完成。

## 下一階段

只有本 vertical slice 通過後，才依序加入：

```text
Wall
Beam
Stair
Slab / closed faces
Door / Window
multi-floor consistency
BIM / IFC
```

## Acceptance Criteria

使用真實案件時，無需人工逐線描圖，即可產生可驗證的：

```text
Grid
+
Dimension
+
Column
→ DrawingIR
→ 1:1 DXF
→ Validation Report
```
