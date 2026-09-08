---
number: 0015
title: Agent Evidence Workflow 與工具使用邊界
status: proposed
date: 2026-09-08
supersedes:
superseded_by:
---

# 0015. Agent Evidence Workflow 與工具使用邊界

## 脈絡

真實舊建築圖包含拼接掃描、模糊文字、尺寸鏈、構件表、符號、跨圖引用、矛盾與遺漏。Agent 不應一次看完整張圖後直接產出最終 JSON 或 CAD，而應逐步檢查、選擇工具、取得證據，再決定下一步。

## 決定

Agent 採循環：

```text
Observe
→ Decide
→ Use Tool
→ Receive Evidence
→ Update Reconstruction State
→ Decide Next Action
```

不是：

```text
Image → LLM → Final CAD
```

## Agent 可以做什麼

- 判斷圖面類型與局部語義；
- 決定要檢查哪一區；
- 呼叫 OCR、segmentation、line detection、measurement、solver 等工具；
- 建立 Observation；
- 提議 Constraint；
- 標記不確定與 Conflict；
- 要求人工確認。

## Agent 不可以做什麼

- 編造正式座標；
- 直接操作 DXF primitive；
- 靜默修改尺寸；
- 忽略 validation error；
- 自行提高 iteration / tool-call limit；
- 將 unresolved conflict 宣告為 resolved。

## Tool taxonomy

### Inspection

```text
inspect_sheet
inspect_region
crop_region
enhance_region
```

### Reading

```text
read_text
read_dimension
read_tag
read_schedule
```

### Vision

```text
segment_concept
segment_box
segment_instances
detect_lines
detect_contours
```

### Geometry

```text
fit_rectangle
fit_parallel_lines
find_intersections
build_planar_graph
find_closed_faces
```

### Solver

```text
solve_grid_coordinates
solve_dimension_chain
solve_entity_geometry
```

### Validation

```text
check_dimension_closure
check_topology
compare_overlay
find_conflicts
```

## Tool Call Audit

每次 tool call 都必須建立可審計紀錄，至少包括：

```text
tool_name
arguments_hash
result_refs
provider/model/version
agent_iteration
duration
timestamp
```

禁止記錄 OpenRouter API key、farside credential、完整 secret 或不必要的大型 base64 payload。

工具建立的新 Observation / Constraint 必須透過 provenance 回指 ToolCallRecord 與 source image region。

## Orchestrator 邊界

Agent 可以選擇下一個 tool，但 orchestrator 控制：

```text
max_iterations
max_tool_calls
timeout
budget
validation thresholds
```

延續 ADR-0013 的原則：Agent 負責推理，程式負責控制。

## 可恢復性

Reconstruction state 必須可序列化。Job 可以因 GPU unavailable、人工確認、預算或 timeout 暫停，再從既有 Observation / Constraint / ToolCallRecord 繼續，不必重跑整份圖。

## Acceptance Criteria

1. 所有 Agent tool call 可追蹤。
2. Agent 不具低階 CAD primitive tool。
3. Solver 結果不由 LLM 生成。
4. Tool failure 不會被靜默忽略。
5. Reconstruction 可暫停並恢復。
6. Agent 產出的 domain proposal 必須通過 schema validation。
