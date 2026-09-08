---
number: 0016
title: Geometry Extraction 與 In-Scale Reconstruction
status: proposed
date: 2026-09-08
supersedes:
superseded_by:
---

# 0016. Geometry Extraction 與 In-Scale Reconstruction

## 脈絡

Paper-to-BIM 必須產生正式 1:1 CAD / BIM geometry，而不是依掃描 pixel 描圖。

舊圖可能具有掃描縮放、紙張變形、影印比例誤差、skew、tile 之間不同 scale。即使 Vision Tool 可以精確抓到物件 outline，pixel distance 仍不得直接成為正式尺寸。

## 決定

正式 geometry authority 為：

```text
Dimension
+
Semantic Relationship
+
Constraint
+
Deterministic Solver
```

而不是 pixel coordinate。

## Canonical Unit

DrawingIR 永遠使用：

```text
millimetre
1 unit = 1 mm
```

圖紙標示比例 1:50、1:100、1:200 等只屬於 source metadata。

## Evidence hierarchy

正式重建時的優先度：

```text
1. 明確尺寸標註
2. 尺寸鏈 / 總尺寸
3. 軸線、標高、構件表與明確數值
4. 建築／結構拓樸關係
5. 經校正的影像量測
6. raw pixel measurement
```

Pixel geometry 是 evidence，不是 metric truth。

## Geometry Regularization

例如 segmentation 得到近似矩形柱，但證據顯示：

```text
C3
800 × 800 mm
位於 B × 4 軸交點
```

Solver 應建立：

```text
800 × 800 mm rectangle
centered at B × 4
```

而不是直接使用 mask polygon。

## Constraint Types

至少支援：

```text
DISTANCE
COINCIDENT
PARALLEL
PERPENDICULAR
CENTERED
COLLINEAR
EQUAL
CLOSED_LOOP
OFFSET
```

Constraint 必須區分 hard / soft，並保留 evidence refs 與 confidence。

## Topology Tools

新增幾何拓樸能力：

```text
build_planar_graph
find_closed_faces
find_connected_components
```

用於後續 slab region、room、wall loop、structural bay 等重建。

## Conflict Handling

若：

```text
A-B + B-C + C-D != A-D
```

不得平均、不得靜默修正。建立 Conflict 並保留所有原始 Evidence，交由後續 validation / human review。

## Determinism

相同的 validated Observations + Constraints 必須產生相同 DrawingIR geometry。LLM model、prompt wording 或 tool-call 順序不得改變已確定 solver result。

## Acceptance Criteria

1. DrawingIR geometry 使用 mm。
2. Raw pixel scaling 不直接產正式 geometry。
3. 尺寸鏈可 deterministic solve。
4. 矛盾尺寸產生 Conflict。
5. Vision mask 可作 evidence，但不能直接成 CAD geometry。
6. 相同 Constraint input 產生相同 DrawingIR。
