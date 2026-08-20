---
name: n2d-supervisor
description: Supervisor agent layer for n2d. Use when asked to run/coordinate the n2d pipeline as an agentic workflow, inspect the next action, dispatch to script/visual/qc specialists, generate context packs and creative-loop packets, or explain where human approval is required. It consumes `skills/n2d/run.py next --json` and never replaces `_进度.md`, stage contracts, gates, batch queue, or production ledger. Triggers n2d supervisor, n2d agent, agentic n2d, 自动总控, 代理编排, 专家派发, context pack, creative loop.
---

# n2d-supervisor — n2d Agentic Runtime 上层总控

`n2d-supervisor` 是 n2d 的**上层 agent 编排层**，不是新的生产状态机。它保留现有 skill 作为“领域知识 + 确定性工具 + 契约”，只负责：

1. 调 `python3 skills/n2d/run.py next <作品根> [第N集] --json` 取得 NextAction。
2. 自动使用 NextAction 里的 `context_pack` / `creative_loop` / `action_contract`。
3. 按 stage 派发少量 specialist：`n2d-script-agent`、`n2d-visual-agent`、`n2d-qc-agent`、`n2d-producer-agent`。
4. 普通、可逆选择默认消费 `run.py` 已落档的推荐值；`needs_stage_execution` 直接派发对应 specialist。只在项目显式设为逐项询问才对 `needs_choice` 停下，而 `needs_payment_confirm` / `needs_compliance` / `needs_acceptance_signoff` / gate block 始终交给用户或原 stage skill。
5. 绝不自行花钱、绝不绕过 gate、绝不直接改 `_进度.md`、绝不自作主张换后端。
6. 读取 `episode_graph_<集>.json` 追踪 storyboard→route→job→media→粗剪→母版→发布裁决，并读取 `blocking_bundles/latest_<集>.json` 判断当前停因；两者都是派生视图，不能覆盖状态机或 gate。

## 边界

- `_进度.md` + `skills/n2d/_lib/n2d_contract.py` 仍是生产状态真值。
- `run.py` 仍是确定性前置和 stop-point 真值。
- `n2d-batch` 仍是多集队列/重试/预算真值。
- `n2d-dashboard` / `production_events.jsonl` 仍是生产事件和成本真值。
- supervisor 只输出/写入 `生产数据/supervisor/` 下的计划，不代替阶段产物。
- context pack 对 `_设置.md` 只投影 `settings` helper 认定的当前设置区（`## 记录` 之前）及其 source；完整审计历史仍留在原文件但不进入 preview。最多附 3 条显式“校正/更正”记录且一律标为非权威 provenance，不能覆盖当前设置；解析失败时留空并报错，不得回退为全文 preview。
- `生产数据/flow_events.jsonl` / `flow_telemetry.json` 只记控制面阶段、停因、缓存命中、adapter 里程碑与耗时；不记 prompt、密钥或供应商原始响应。它与 dashboard 的成本/QA 账本互补，不取代 `production_events.jsonl`。
- `run.py next --preview` 不写 episode graph、blocking bundle 或 flow telemetry；正式 `next` 才原子落盘。

## 命令

```bash
python3 skills/n2d/n2d-supervisor/scripts/supervisor.py next <作品根> [第N集] --write --json
python3 skills/n2d/n2d-supervisor/scripts/supervisor.py next <作品根> [第N集] --write
```

输出包含：
- `next_action`：原始 `run.py next` 结构化结果；
- `dispatch`：应由哪个 specialist 处理；
- `human_gate`：是否必须问用户；
- `allowed_operations` / `forbidden_operations`：本轮 agent 边界；
- `outputs`：写盘 JSON/MD 路径。

## Specialist 规则

完整配置见 `references/specialists.json`。简表：

| specialist | 管什么 | 不允许 |
|---|---|---|
| `n2d-script-agent` | 剧本、分镜、题材母题、爽点钩子 | 花钱、直接回写进度 |
| `n2d-visual-agent` | 出图/视频 prompt、资产/身份/动作契约 | 花钱生成、绕过路由 |
| `n2d-qc-agent` | gate、score、ledger、review-ui、返工范围 | 人工签收、无依据放行 |
| `n2d-producer-agent` | 选择点、预算、合规、batch、停线 | 擅自换后端、越过确认 |
