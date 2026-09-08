---
number: 0014
title: Semantic Vision Tool Layer 與 Segmentation Provider
status: proposed
date: 2026-09-08
supersedes:
superseded_by:
---

# 0014. Semantic Vision Tool Layer 與 Segmentation Provider

## 脈絡

Paper-to-BIM 的目標不是 raster tracing，而是讓 Agent 理解圖面、主動使用工具收集證據，再由 deterministic solver 產生 1:1 DrawingIR。

ADR-0010 已確立 Understanding First：VLM 判斷「這是什麼」，CV／Vision Tool 負責量測「在哪裡、範圍多大」。目前仍缺少一層正式能力：已知某物件可能是柱、牆、樓梯等之後，如何精確取得其 mask、outline、polygon、edge evidence。

## 決定

新增 **Semantic Vision Tool Layer**：

```text
semantic request
→ detection / segmentation
→ mask
→ contour
→ polygon / edge evidence
```

此層輸出屬於 Observation / Evidence，不得直接成為 DrawingIR geometry。

### Provider abstraction

定義：

```text
SegmentationProvider
```

至少支援：

```text
segment_concept(...)
segment_box(...)
segment_points(...)
segment_instances(...)
capabilities(...)
```

可能實作者：

```text
SamProvider
YoloSegProvider
GroundedSegProvider
FutureFineTunedProvider
```

Paper-to-BIM domain 不得依賴特定 segmentation model。

## Agent 可用工具

Vision tools：

```text
vision.segment_concept
vision.segment_box
vision.segment_points
vision.segment_instances
```

影像／幾何後處理：

```text
geometry.mask_to_contours
geometry.contours_to_polygon
geometry.simplify_polygon
geometry.fit_rectangle
geometry.fit_parallel_lines
geometry.skeletonize
geometry.find_intersections
```

## Mask 不等於 CAD

Segmentation 只能回答「物件在影像中大約佔哪些像素」。

例如柱的 mask polygon 不得直接成為正式柱幾何。正式柱 geometry 必須結合：

```text
column tag
+
column schedule
+
grid intersection
+
dimension constraints
```

由 solver 建立。

## 模型策略

固定建築類別，例如 column、beam、wall、door、window、stair，適合 instance segmentation model。

未知物件、Agent 指定局部區域、互動式人工修正，可使用 promptable segmentation model。

本 ADR 不指定唯一模型。

## 授權原則

任何 Vision Provider 在進入 production 前必須建立可審查的 model/license metadata：

```text
model
library
weights
license
commercial_use
SaaS/API restriction
redistribution
```

「已有 container image」不等於已取得商業授權。

## 後果

優點：

- Vision model 可替換；
- Paper-to-BIM 不綁死 SAM、YOLO 或單一 vendor；
- pixel evidence 與 engineering geometry 明確分離；
- 可逐步導入自研建築圖模型。

代價：

- 多一層 provider abstraction；
- 需要 mask → contour → geometry evidence 後處理；
- segmentation 不能直接輸出 CAD。

## Acceptance Criteria

1. Agent 可以呼叫 segmentation tool。
2. Provider 可替換。
3. Segmentation 結果保留 provenance。
4. mask / polygon 只建立 Evidence / Observation。
5. DrawingIR 不依賴任何 Vision Provider。
6. production provider 必須有 license metadata。
