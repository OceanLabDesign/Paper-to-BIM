---
number: 0017
title: Farside Vision API 整合邊界
status: proposed
date: 2026-09-08
supersedes:
superseded_by:
---

# 0017. Farside Vision API 整合邊界

## 脈絡

部分 Vision workload，例如 segmentation / detection，需要 GPU。Paper-to-BIM 不應自行管理 GPU infrastructure。

OceanLab 已有 farside.work，可提供按需 GPU runtime；同一項 GPU Vision capability 同時應可被 farside 使用者直接使用、由第三方透過 API 使用，以及被 Paper-to-BIM Agent 當工具使用。

## 決定

Paper-to-BIM 將 farside 視為外部 GPU capability provider。

依賴方向：

```text
Paper-to-BIM
    ↓ API
Farside Vision
    ↓
GPU Runtime
```

禁止：

```text
Paper-to-BIM import farside internal modules
```

## Adapter

Paper-to-BIM 建立：

```text
FarsideVisionProvider
```

實作 ADR-0014 的 `SegmentationProvider`。

Paper-to-BIM 不得把 farside 設為唯一 implementation；本機、其他雲端或未來自建 provider 仍可替換。

## API Contract

概念 API：

```text
POST /v1/segment/concept
POST /v1/segment/box
POST /v1/segment/points
POST /v1/segment/instances
GET  /v1/jobs/{id}
GET  /v1/jobs/{id}/artifacts
```

實際 protocol 可同步或 asynchronous job，但 semantic result contract 必須穩定。

## 回傳內容

Farside Vision 只回傳 Vision evidence，例如：

```text
instance_id
bbox
mask_ref
polygon
score
model_id
model_version
provider
runtime metadata
```

禁止 farside Vision API 回傳：

```text
ColumnEntity
WallEntity
DrawingIR
DXF
```

建築 domain interpretation 屬於 Paper-to-BIM。

## Data / Artifact Boundary

大圖與 mask 優先以 artifact reference / signed object reference 傳遞，不在 tool audit log 中複製完整 base64 payload。

所有外部 Vision result 必須能建立 provenance，至少指向：

```text
source image / region
farside job id
provider/model/version
tool call id
result artifact refs
```

## Failure Tolerance

若 farside 不可用，Paper-to-BIM 應：

- 保留 reconstruction job；
- 標記 tool unavailable / pending；
- 可重新執行；
- 不破壞既有 Observation / Constraint / DrawingIR；
- 不將暫時失敗誤標為建築圖面 Conflict。

## Billing Boundary

Paper-to-BIM 可以記錄 farside usage / cost reference，但 Paper-to-BIM domain object 不包含 billing logic。GPU 計量與計價由 farside 負責；Paper-to-BIM 只保存必要 usage attribution。

## Acceptance Criteria

1. P2B 不需要本地 GPU 即可啟動。
2. GPU tool 只在需要時呼叫。
3. Vision Provider 可換成非 farside provider。
4. farside outage 不損壞 reconstruction state。
5. API response 可以完整建立 provenance。
6. farside 不需要理解 Paper-to-BIM 的建築 Entity ontology。
