---
number: 0013
title: Agent Tool Runtime + OpenRouter BYOK Model Provider
status: proposed
date: 2026-09-08
supersedes:
superseded_by:
---

# 0013. Agent Tool Runtime + OpenRouter BYOK Model Provider

## 脈絡

Paper-to-BIM 的產品目標不是 raster tracing，也不是讓多模態模型直接吐 CAD 座標。

目標是讓 Agent：

1. 看懂建築圖面與圖面語意；
2. 判斷自己缺少哪些資訊；
3. 主動呼叫受控工具量測、裁切、校正、建立尺寸鏈與求解幾何；
4. 將圖面資訊轉成可追溯的 Observation / Constraint；
5. 由 deterministic solver 建立 in-scale DrawingIR；
6. 由 exporter 正式繪製 1:1 DXF / BIM，而不是描圖。

模型供應層採 OpenRouter，使用者自行提供 OpenRouter API Key 並選擇模型。系統本身不綁死 Claude、OpenAI、Gemini 或其他單一模型。

## 決定

採用以下責任鏈：

```text
User Drawing
    ↓
Agent Runtime
    ├── Vision Model (via OpenRouter)
    ├── Read-only Inspection Tools
    ├── Measurement Tools
    ├── Constraint Tools
    ├── Solver Tools
    └── Review Tools
          ↓
Observation / Constraint Store
          ↓
Deterministic Geometry Solver
          ↓
DrawingIR (mm, 1:1)
          ↓
Exporter
```

### 一、OpenRouter 是 Model Gateway，不是 Domain Dependency

建立新的 adapter：

```text
adapters/llm/openrouter.py
```

Domain、solver、exporter 不得 import OpenRouter client。

Agent runtime 只透過抽象介面使用模型：

```python
class ModelProvider:
    def complete(...): ...
    def capabilities(model_id): ...
```

OpenRouter adapter 實作該介面。

### 二、BYOK

使用者自行輸入：

```text
OPENROUTER_API_KEY
model_id
```

例如：

```text
openai/...
anthropic/...
google/...
qwen/...
```

系統不得將使用者 API Key：

- 寫入 DrawingIR；
- 寫入 case artifacts；
- 寫入 log；
- 寫入 Git repo；
- 傳給 exporter；
- 傳給 MCP client。

第一階段 key 僅透過 runtime config / process environment 傳入 provider adapter。
若未來加入 GUI credential persistence，必須另立 ADR 定義 OS keychain / encrypted secret storage；不得明文寫入專案設定檔。

### 三、模型不是任意選了就能跑完整流程

Paper-to-BIM 的 Agent 至少需要能力：

```text
vision_input
structured_output
function_tools
```

建議能力：

```text
pdf_input
reasoning
large_context
```

因此建立 `ModelCapabilities`。

使用者可以選任意 OpenRouter model，但啟動 reconstruction job 前必須做 capability gate。

例如：

```text
模型沒有 vision       → 禁止用於 drawing understanding
模型沒有 tools        → 禁止用於 agent tool loop
模型沒有 structured output → 只能進 compatibility mode，不得直接進 production reconstruction
```

UI 不應只顯示模型名稱，而應顯示是否符合 Paper-to-BIM reconstruction profile。

### 四、Agent 不直接繪圖

Agent 不能呼叫 `ezdxf.add_line(x1,y1,x2,y2)` 類低階 CAD API。

Agent 可用的工具應是語意化工具，例如：

```text
inspect_region
read_dimension
measure_segment
find_grid_axes
calibrate_scale
build_dimension_chain
add_constraint
solve_constraints
inspect_solution
request_human_review
```

Exporter API 不暴露給模型作自由繪圖。

正確流程：

```text
Agent
  ↓ tools
Observation + Constraint
  ↓ solver
DrawingIR
  ↓ exporter
DXF / IFC
```

而不是：

```text
Agent → CAD commands
```

### 五、Tool 分為四級

#### A. Inspection Tools
不改 domain state：

```text
inspect_page
inspect_region
crop_region
enhance_region
list_observations
get_observation
```

#### B. Measurement Tools
產生 Measurement Observation：

```text
measure_pixel_distance
measure_line_angle
calibrate_scale
read_dimension_candidates
trace_axis_candidate
```

#### C. Reconstruction Tools
建立 domain proposal，不直接輸出 CAD：

```text
propose_observation
propose_constraint
link_evidence
mark_ambiguous
report_conflict
```

#### D. Solver Tools
呼叫 deterministic code：

```text
solve_dimension_chain
solve_grid_coordinates
solve_constraints
validate_closure
validate_geometry
```

Agent 可以選擇何時呼叫，但 solver 的數學結果不是由模型生成。

### 六、所有 Tool Call 必須可審計

每次 tool execution 建立：

```text
ToolCallRecord
```

至少記錄：

```text
call_id
tool_name
arguments_hash
result_refs
model_id
iteration
timestamp
```

不得把 API key、完整 base64 圖片或其他 secret 記入 ToolCallRecord。

Tool call 產生的新 Observation / Constraint 必須透過 provenance 指回 ToolCallRecord 與 source image region。

### 七、Structured Output 是 Agent/Domain 邊界

模型自由文字不得直接成為 domain object。

模型要建立 Observation / Constraint 時必須通過 schema validation。

模型輸出流程：

```text
Model response
   ↓ structured schema
Proposal
   ↓ validator
Domain object
```

validator failure 由 orchestrator 處理；模型不能自行宣告「格式差不多就算了」。

### 八、Agent Loop 由程式控制

延續既有 deterministic orchestrator 原則。

Agent 可以：

- 選擇下一個 tool；
- 分析 tool result；
- 建議完成。

Agent 不可以：

- 無限迴圈；
- 自行提高 iteration limit；
- 規避 validation；
- 直接決定 unresolved conflict 已解決。

Runtime 由設定限制：

```text
max_iterations
max_tool_calls
max_image_regions
max_retries_per_schema
```

### 九、In-scale 的定義

「In scale」在本系統不是依 scan pixel scale 描線。

正式幾何座標來源優先序：

```text
1. 明確尺寸標註 / 尺寸鏈
2. 標高、軸線、構件尺寸等圖面數值
3. 已校正的量測尺度
4. 幾何／建築約束推導
5. 像素量測（僅 soft evidence / fallback）
```

DrawingIR canonical unit 預設為：

```text
millimeter
```

Exporter 輸出 Model Space：

```text
1 unit = 1 mm
```

原始圖面即使 1:100、1:50、掃描拉伸或變形，最終 DrawingIR 仍表示真實建築尺寸。

### 十、第一個 Agent Vertical Slice

第一個可驗證功能只做：

```text
平面圖局部
→ Agent 看圖
→ inspect / crop
→ 找 grid axis
→ 讀尺寸
→ 建 dimension chain
→ solver 求 grid coordinates
→ 找柱編號與柱尺寸
→ 建 Column Entity
→ DrawingIR(mm)
→ DXF
→ overlay / validation report
```

Acceptance 不要求完整平面圖。

## Acceptance Criteria

1. 使用者可提供 OpenRouter API key 與 model id。
2. API key 不寫入 case、log、DrawingIR 或 artifact。
3. OpenRouter adapter 不被 domain / solver / exporter import。
4. Reconstruction profile 檢查 vision + tools + structured output 能力。
5. Agent 至少可以呼叫 inspection、measurement、constraint、solver 四類工具。
6. Agent 不得直接呼叫低階 CAD primitives。
7. 所有正式座標由 solver / validated measurement 產生。
8. DrawingIR 使用 mm，exporter 以 1 unit = 1 mm 輸出。
9. 每個 Entity 可追溯到 Observation → ToolCall → Source Region。
10. 模型切換不要求修改 domain model 或 solver。

## 後果

Paper-to-BIM 的核心產品不再是「某個 VLM 辨識舊圖」，而是一個 model-agnostic architectural reconstruction runtime。

模型負責理解與決策工具使用；工具負責取得可靠證據；solver 負責幾何；DrawingIR 保存真實模型；exporter 負責正式繪圖。

這個分工是後續從 CAD 擴展到 BIM 的前提。
