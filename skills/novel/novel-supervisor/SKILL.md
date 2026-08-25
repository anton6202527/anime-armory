---
name: novel-supervisor
description: Durable upper-layer producer/supervisor for one-click novel production. It reads the canonical pipeline/revision/QA/batch signals, returns the next safe action, and `producer.py` repeatedly executes reversible deterministic commands or project-local specialist adapters while feeding real execution telemetry to the circuit breaker. It never writes prose itself or crosses rights, explicit human-required, tied-evidence conflict, circuit-breaker, irreversible publish, or final hash-bound acceptance boundaries. Use when asked to run/coordinate/resume the novel pipeline or automatically revise toward a final deliverable. Triggers novel supervisor, novel agent, agentic novel, 自动小说总控, 一键成书, 创作闭环, 自动修稿.
---

# novel-supervisor — 小说生产线 durable producer / supervisor

`novel-supervisor` 是 novel 生产线的**上层 agent 编排层**。它不替代 `novel-craft` 的确定性写入或 `novel-review` 的检验，而是读取 `pipeline_runner` 的阶段计划、`revision_plan`、语义任务、batch 队列和 QA 报告，给出下一步安全派发动作。

`supervisor.py` 产 `next action`；`producer.py` 持有 durable loop，连续执行无占位符的可逆确定性命令，并通过项目级 specialist adapter 派发语义写作/审阅。它不直接写正文、不自行选择模型或批准费用。默认将蓝图/设定/Demo 的常规可逆审阅派发给独立 specialist；显式人审、高风险与最终验收边界仍停下。

业务状态只认 `_进度.md`，pipeline run / author workflow / dashboard / producer run 都标成派生或执行视图。最终完成只认 `导出/completion_verdict.json`：当前 release manifest 为 machine-ready 且 `导出/final_acceptance.json` 具名绑定同一个 `release_digest`，才是 `accepted`。

> **没有 LLM「评委/辩论」环节。** 本层的「批判/把关」是**确定性的结构化信号读取**——读 `review_report.json` 的 blocking finding、`revision_plan` 的 P0/冲突、batch 死信、语义任务状态，按规则给下一步，不挂任何开放式 LLM 评委（遵循 novel-* 设计法「别挂 LLM 评委，先抽结构再判」）。若未来要加 Writer-Critic-Editor 式迭代，也必须 checklist-grounded（对照读者契约/弧光/伏笔账本），且经成本闸控；不得引入凭感觉的 LLM 互评。**可选 critic 的完整 spec（触发条件 / checklist 绑定 / perspective-diverse 镜头 / 成本闸 / 落地边界）见 [`references/critic-loop.md`](references/critic-loop.md)——绝不进 post_write 常开主路；触发面已接线（2026-07）：`supervisor.py` 的 `signals.critic_loop` 会读 `_设置.md` 的 `critic_loop` 选择点，开启时在 next_action 信号里提示"高权重章过确定性闸后按 spec 跑 critic"，评委 verdict 必须过 `novel/_lib/judge_protocol.py` 去偏后才可采信。**

## 核心能力与边界

1. **自愈闭环**：若 `review_report.json` 有 blocking finding 且缺 `revision_plan.json`，先返回 `build_revision_plan`，把问题收敛为统一修订计划，而不是让各报告各自改稿。
2. **动态派发**：基于 `novel/scripts/pipeline_runner.py` 的 dry-run plan，选择 `workflow_orchestrator` / `specialist_writer` / `specialist_reviewer` / `specialist_score`。
3. **语义任务优先**：若 `语义任务/*.json` 仍 open，先提示领取/完成语义任务，保证 report/score/ledger 都绑定 source snapshot。
4. **batch 安全**：若 `novel-batch` 出现 dead-letter，先阻断并要求查死信，不继续自动派发后续阶段。
5. **风险分级审阅**：默认 `审阅策略=用户授权制作代理` 时，`blueprint`、`setting`、`demo` 返回 `dispatch`，由独立 specialist 实际复核；前两者用 `pipeline_runner.py --approve-stage ... --delegated --agent delegate:... --reason ...` 记录与当前输入/产物 hash 绑定的代理批准。显式 `逐阶段用户确认`、`human_required` 任务、权利/合规、跨来源冲突、不可逆发布和最终验收仍返回 `needs_human`。初始化骨架文件永远不算通过。
6. **双层熔断（须接执行遥测才生效）**：`record-execution` 按 `stage + run_id + finding_hash` 精确记录；同时维护 `stage + finding_hash` rolling breaker，跨 run 同一问题连续失败会进入 60 分钟冷却并要求人工介入。**诚实边界**：熔断器是被动账本——**只有执行方在每次 started/failed/succeeded 后调用 `record-execution` 喂遥测，它才有数据可判**；从不有人回报时它处于 inert（永不触发，不会凭空保护流程）。`next` 输出的 `circuit_breaker.armed` 字段显式标明当前是否接到遥测（`false`=未接·静默不保护），避免把空账熔断器误读成"已在守护"。
7. **长篇动态章纲**：每 5 个已写章节检查一次未来章纲 delta；只影响未写章、未触碰 author intent/核心结局/读者契约且冲突有明确证据优势时自动应用，否则才停。
8. **修订事务**：统一修订计划按 macro-before-micro 顺序进入 Story-VCS 分支；writer 编辑候选、独立 reviewer 以 candidate hash 验证，合并后红色机检自动 rollback。

## 典型工作流

```bash
python3 skills/novel/novel-supervisor/scripts/supervisor.py run "<作品根>" --write-plan --write
python3 skills/novel/novel-supervisor/scripts/supervisor.py run "<作品根>" --json
python3 skills/novel/novel-supervisor/scripts/supervisor.py start-run "<作品根>" --agent orchestrator
python3 skills/novel/novel-supervisor/scripts/supervisor.py show-run "<作品根>"
python3 skills/novel/novel-supervisor/scripts/supervisor.py record-execution "<作品根>" \
  --stage review --run-id run_YYYYMMDD_HHMMSS --finding-hash "<finding_hash>" --result failed
python3 skills/novel/novel-supervisor/scripts/producer.py "<作品根>" --max-cycles 60
python3 skills/novel/novel-supervisor/scripts/producer.py "<作品根>" --plan-only --json
```

语义 adapter 登记在 `<作品根>/生产数据/novel_specialist_execution_adapters.json`，按 `specialist_writer` / `specialist_reviewer` / `specialist_score` 配 `command` token 数组；用 `{request}` 接收 producer 生成的请求 JSON。没有 adapter 时 producer 明确停在 `specialist_adapter_required`，不假装已写或已审。

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
- `生产数据/producer/producer_run.json`（执行收据，不是第二套业务状态）
