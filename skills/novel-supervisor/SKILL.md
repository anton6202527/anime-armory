---
name: novel-supervisor
description: Read-only next-action recommender (上层 agent 编排层) for novel production. Reads pipeline_runner plans, revision plans, review/QA reports, batch queue and circuit-ledger signals, then returns the next safe action (recommended commands + agent role + handoff). It does NOT execute, loop, call a model, or write prose, and never bypasses manual approval steps like blueprint or setting bibles; its 批判/把关 is deterministic structured-signal reading, not an LLM judge (an optional checklist-grounded critic is spec-only and unwired). Use when asked to run/coordinate the novel pipeline, get the next step, or route blockers to a specialist skill. Triggers novel supervisor, novel agent, agentic novel, 自动小说总控, 创作闭环, 自动修稿.
---

# novel-supervisor — 小说生产线「下一步动作」推荐器（只读编排层）

`novel-supervisor` 是 novel 生产线的**上层 agent 编排层**。它不替代 `novel-craft` 的确定性写入或 `novel-review` 的检验，而是读取 `pipeline_runner` 的阶段计划、`revision_plan`、语义任务、batch 队列和 QA 报告，给出下一步安全派发动作。

它只产 `next action`，不直接写正文、不调用模型、不绕过蓝图/设定/Demo 等人工确认边界。

> **没有 LLM「评委/辩论」环节。** 本层的「批判/把关」是**确定性的结构化信号读取**——读 `review_report.json` 的 blocking finding、`revision_plan` 的 P0/冲突、batch 死信、语义任务状态，按规则给下一步，不挂任何开放式 LLM 评委（遵循 novel-* 设计法「别挂 LLM 评委，先抽结构再判」）。若未来要加 Writer-Critic-Editor 式迭代，也必须 checklist-grounded（对照读者契约/弧光/伏笔账本），且经成本闸控；不得引入凭感觉的 LLM 互评。**可选 critic 的完整 spec（触发条件 / checklist 绑定 / perspective-diverse 镜头 / 成本闸 / 落地边界）见 [`references/critic-loop.md`](references/critic-loop.md)——目前仅 spec、未接线，绝不进 post_write 常开主路。**

## 核心能力与边界

1. **自愈闭环**：若 `review_report.json` 有 blocking finding 且缺 `revision_plan.json`，先返回 `build_revision_plan`，把问题收敛为统一修订计划，而不是让各报告各自改稿。
2. **动态派发**：基于 `novel/scripts/pipeline_runner.py` 的 dry-run plan，选择 `workflow_orchestrator` / `specialist_writer` / `specialist_reviewer` / `specialist_score`。
3. **语义任务优先**：若 `语义任务/*.json` 仍 open，先提示领取/完成语义任务，保证 report/score/ledger 都绑定 source snapshot。
4. **batch 安全**：若 `novel-batch` 出现 dead-letter，先阻断并要求查死信，不继续自动派发后续阶段。
5. **人类边界**：不会绕过 `blueprint`、`setting`、`demo` 或带 human gate 的阶段。
6. **双层熔断（须接执行遥测才生效）**：`record-execution` 按 `stage + run_id + finding_hash` 精确记录；同时维护 `stage + finding_hash` rolling breaker，跨 run 同一问题连续失败会进入 60 分钟冷却并要求人工介入。**诚实边界**：熔断器是被动账本——**只有执行方在每次 started/failed/succeeded 后调用 `record-execution` 喂遥测，它才有数据可判**；从不有人回报时它处于 inert（永不触发，不会凭空保护流程）。`next` 输出的 `circuit_breaker.armed` 字段显式标明当前是否接到遥测（`false`=未接·静默不保护），避免把空账熔断器误读成"已在守护"。

## 典型工作流

```bash
python3 skills/novel-supervisor/scripts/supervisor.py run "<作品根>" --write-plan --write
python3 skills/novel-supervisor/scripts/supervisor.py run "<作品根>" --json
python3 skills/novel-supervisor/scripts/supervisor.py start-run "<作品根>" --agent orchestrator
python3 skills/novel-supervisor/scripts/supervisor.py show-run "<作品根>"
python3 skills/novel-supervisor/scripts/supervisor.py record-execution "<作品根>" \
  --stage review --run-id run_YYYYMMDD_HHMMSS --finding-hash "<finding_hash>" --result failed
```

`run` / `next` 输出：

- `status`: `dispatch` / `self_healing` / `needs_human` / `blocked` / `complete`
- `next_stage`
- `agent_role`
- `recommended_commands`
- `handoff`（当可派发时）
- `signals`（语义任务、review blockers、revision、batch）

写盘产物：

- `生产数据/supervisor_next_action.json`
- `生产数据/supervisor_ledger.json`（只由 `record-execution` 写入；`run` / `next` 只读，不会因为反复查看状态误触发熔断。失败按 `stage + run_id + finding_hash` 精确记录，调度决策按当前 stage 聚合 exact 与 rolling entries：任一 run/finding 三连失败，或同一 finding 跨 run 三连失败，都会停止自愈派发）
