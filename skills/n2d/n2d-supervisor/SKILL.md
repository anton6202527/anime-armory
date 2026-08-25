---
name: n2d-supervisor
description: Durable supervisor/producer layer for n2d. Use when asked to run/coordinate the n2d pipeline as an agentic or one-click workflow, keep advancing through reversible work, dispatch script/visual/qc specialists, execute authorized stage commands, generate context packs and creative-loop packets, or explain a true human boundary. It consumes `skills/n2d/run.py next --json` and never replaces `_进度.md`, stage contracts, gates, batch queue, or production ledger. Triggers n2d supervisor, n2d producer, n2d agent, agentic n2d, 一键成片, 自动总控, 代理编排, 专家派发, context pack, creative loop.
---

# n2d-supervisor — n2d Agentic Runtime 上层总控

`n2d-supervisor` 是 n2d 的**上层 agent 编排层**，不是新的生产状态机。它保留现有 skill 作为“领域知识 + 确定性工具 + 契约”，只负责：

1. 调 `python3 skills/n2d/run.py next <作品根> [第N集] --json` 取得 NextAction。
2. 自动使用 NextAction 里的 `context_pack` / `creative_loop` / `action_contract`。
3. 按 stage 派发少量 specialist：`n2d-script-agent`、`n2d-visual-agent`、`n2d-qc-agent`、`n2d-producer-agent`。
4. 普通、可逆选择默认消费 `run.py` 已落档的推荐值；`needs_stage_execution` 直接派发对应 specialist。付费阶段若当前 fresh plan、producer binding、模型/渠道、scope 与 canonical input SHA 都命中尚有余量的 v2 envelope，`run.py` 会把原付款停点收敛为 authorized `needs_stage_execution`，supervisor 继续派发 exact `n2d-batch` runner 路径；只有缺包、过期、超额、成本未知或合同/哈希变化时才保留 `needs_payment_confirm`。项目显式设为逐项询问时才对普通 `needs_choice` 停下；`needs_compliance`、`needs_acceptance_signoff` 与 gate block 始终交给用户或原 stage skill。
5. `producer.py` 持久持有当前作品：每轮重新消费 NextAction，自动执行已登记的安全修复、项目 specialist adapter、无付费本地命令或已获阶段预算包授权的 exact batch 命令，直到 canonical `done` 或真实硬边界；同一前沿反复出现时以 `non_convergent` 停止，避免死循环。
6. 绝不自行签发/扩大预算、绝不绕过 gate、绝不直接改 `_进度.md`、绝不自作主张换后端。
7. 读取 `episode_graph_<集>.json` 追踪 storyboard→route→job→media→粗剪→母版→发布裁决，并读取 `blocking_bundles/latest_<集>.json` 判断当前停因；两者都是派生视图，不能覆盖状态机或 gate。

## 边界

- `_进度.md` + `skills/n2d/_lib/n2d_contract.py` 仍是生产状态真值。
- `run.py` 仍是确定性前置和 stop-point 真值。
- `n2d-batch` 仍是多集队列/重试/预算真值。
- `n2d-dashboard` / `production_events.jsonl` 仍是生产事件和成本真值。
- supervisor 计划写入 `生产数据/supervisor/`；durable producer 的执行请求/收据写入 `生产数据/producer/`。两者都不代替阶段产物；预算包只读 probe，不 issue、不扩大、不 consume，agent/delegate/auto 身份也不能冒充 human approver。
- context pack 对 `_设置.md` 只投影 `settings` helper 认定的当前设置区（`## 记录` 之前）及其 source；完整审计历史仍留在原文件但不进入 preview。最多附 3 条显式“校正/更正”记录且一律标为非权威 provenance，不能覆盖当前设置；解析失败时留空并报错，不得回退为全文 preview。
- `生产数据/flow_events.jsonl` / `flow_telemetry.json` 只记控制面阶段、停因、缓存命中、adapter 里程碑与耗时；不记 prompt、密钥或供应商原始响应。它与 dashboard 的成本/QA 账本互补，不取代 `production_events.jsonl`。
- `run.py next --preview` 不写 episode graph、blocking bundle 或 flow telemetry；正式 `next` 才原子落盘。

## 命令

```bash
python3 skills/n2d/n2d-supervisor/scripts/supervisor.py next <作品根> [第N集] --write --json
python3 skills/n2d/n2d-supervisor/scripts/supervisor.py next <作品根> [第N集] --write

# 一键持续推进；只在预算/合规/能力/公开发布/最终验收等真实边界停
python3 skills/n2d/n2d-supervisor/scripts/producer.py <作品根> [第N集] --json

# 只预览 producer 会遇到的当前前沿，不执行
python3 skills/n2d/n2d-supervisor/scripts/producer.py <作品根> [第N集] --plan-only --json
```

`producer.py` 的退出码 `0` 只表示 canonical workflow 已返回 `done`；遇硬边界、adapter 缺失、执行失败或不收敛返回 `2`，并把完整 stop receipt 写到 `生产数据/producer/producer_run_<集>.json`。这份 receipt 是执行证据，不是第二套完成状态。

创作工位需要非交互执行器时，在作品内登记 `生产数据/specialist_execution_adapters.json`：

```json
{
  "kind": "n2d_specialist_execution_adapter_registry",
  "adapters": {
    "n2d-visual-agent": {
      "adapter_id": "studio_visual_wrapper_v1",
      "command": ["/absolute/path/to/wrapper", "--request", "{request}"],
      "timeout_seconds": 1800
    }
  }
}
```

wrapper 消费自包含 request JSON，产完该阶段声明的正式产物并走原 stage 校验/回写；它不能签预算、合规、发布或最终验收。没有已登记 wrapper 时 producer 如实停在 `specialist_adapter_required/execution_failed`，不把“给了建议”伪装成完成。

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
