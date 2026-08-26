---
name: n2d-batch
description: "P1 batch task queue and worker runner for n2d. Build/manage a queue from `_进度.md`, with canonical frontier checks, task-bound production authorization, output+post-gate completion commit, max concurrency, failure retry, budget caps, targeted reruns for affected shots/clips/artifacts, and a read-only dry-run. Single-machine multi-worker safety is local & backend-free: atomic flock claim + atomic-write ledger + per-task lease with heartbeat renewal + auto-reclaim of expired leases + --resume for crash recovery (multi-machine still needs a real coordination backend). Use when asked for 批量任务队列, 自动排队, batch runner, worker, 多worker, 并发, 文件锁, 原子认领, 不双认领, 租约, lease, 断点恢复, resume, reclaim, 失败重试, 预算上限, 只重跑受影响镜头, batch, queue, rerun affected n2d work."
---

# n2d-batch — P1 批量任务队列 + Worker Runner

`n2d-batch` 把 n2d 从“单集手工推进”升级成“可排队、可并发、可重试、可控预算、可最小范围重跑”的生产编排层。

- `queue.py`：生成和维护队列账本。
- `runner.py`：worker 执行器，自动 claim、执行配置好的 stage 命令、验证产物与 post gate、写 dashboard telemetry，再提交 done/fail/qa_blocked。

真正的生产逻辑仍归 `n2d-script` / `n2d-voice` / `n2d-image` / `n2d-video` / `n2d-compose`。runner 只调用这些阶段的 shell 命令或本地脚本，不重写阶段逻辑。

## 输入 / 输出 / 读写边界

- **输入**：`_进度.md`、stage contract、P-3 `ai_shooting_schedule` / `ai_shooting_schedule_batch_seed`、gate/review/score/identity findings、`consistency_ledger` root causes、可选 `batch_runner.json` 命令配置。
- **输出**：`生产数据/batch_queue.json/md`、worker claim/lease/mark 状态、runner telemetry、`production_slo.json`、`batch_governance.json/md`、`dead_letter_queue.json/md`。
- **读写边界**：队列层只排任务和调用已配置命令；不内置 stage 业务逻辑、不擅自整集重跑、不绕过对应 skill 的 gate。
- **契约关系**：stage key、owner、输出验收、finding 回流字段来自 `skills/n2d/_lib/n2d_contract.py`；无稳定 readiness，所以登记为 `CROSS_CUTTING_TOOLS` 而不是进度横切就绪项。

## 核心原则

- **路由真值源仍是 `_进度.md` + `n2d/_lib/n2d_contract.py`**：队列只消费现有状态机，不自创阶段顺序。
- **队列是机器账本**：`创作区/制漫剧/<剧名>/生产数据/batch_queue.json` 是机器真值，`batch_queue.md` 供人读。
- **排队默认合并，不覆盖在跑队列**：`plan` 默认在文件锁内合并到现有账本，保留 `running/retry_queued/done/failed` 历史，只刷新未开始的 `queued/blocked_budget` 同 ID 任务；要整队替换必须显式 `--replace`，若队列里有 `running` 还必须再加 `--force`。
- **并发靠 claim，不靠口头分配**：多个 agent/工位从同一队列 `claim` 任务，状态从 `queued/retry_queued` 变 `running`，并发槽由 `max_concurrency` 限制。
- **认领是原子的（单机多 worker 安全）**：默认 `claim/mark/reclaim/renew` 全在 `生产数据/batch_queue.lock` 的 `flock` 互斥锁内"重读最新队列→改→原子写(temp+replace)"——**多进程同抢绝不双认领、不互相覆盖**。注意 flock 跨 NFS 不可靠，真·多机要换协调后端，别靠本锁。
- **SQLite 协调后端（本地工业化优先）**：设置 `N2D_COORDINATION_BACKEND=sqlite`，或在 `生产数据/coordination_backend.json` 写 `{"backend":"sqlite"}` 后，`claim/mark/reclaim/heartbeat` 走 `生产数据/batch_queue.sqlite3` 的 `BEGIN IMMEDIATE` 事务；`batch_queue.json/md` 仍作为便携镜像同步写回。适合单机多 worker、共享项目盘和本地渲染农场的第一档强一致升级；还没到 Redis/Temporal/K8s 的复杂度。发布/放量前用 `queue.py sqlite-doctor <作品根> --write` 检查 schema_version、DB/JSON 镜像一致性、orphan task 和 WAL 状态。
- **worker 只走 exact claim**：动作卡把 `task_id + current_plan_digest + episode + stage` 一次性交给 runner；它在同一临界区物化 fresh plan 并用 `claim_exact` 精确认领，禁止退回“队列第一条可跑任务”。外部协调后端若未实现 exact claim 直接 fail-closed。runner 跑任务期间不持锁；mark 仍校验 worker+attempt，长任务靠心跳续租，避免旧 worker 覆盖新认领。
- **排队不是生产授权**：`voice/image/video/compose` 执行前必须与 `run.py next` 返回的同集 `frontier.stage_key` 完全一致。v1 继续兼容单 task/attempt 的 `production_authorization`；v2 `phase_spend_envelope` 必须精确绑定 line/project/stage/scope、canonical producer input SHA、具体 model/channel、expiry、max_calls/max_attempts/cost ceiling，并同时保存真实 human approver、不可伪造为空的 `approval_reference` 与 `source_quote`（三者均进 authorization digest；`agent:/delegate:/auto:` 身份/证据拒绝）。`attempt_id=phase_retry_round`：同一阶段重试轮内多个 calls 共享 attempt_id，max_attempts 统计唯一轮次；每个物理调用仍须唯一 consumption_id。`run.py`/supervisor 只做当前 fresh plan + producer binding 的只读 probe；只有 probe 返回 authorized 时才给 `needs_stage_execution`，且只允许 exact batch runner 路径。runner 是唯一 consume 边界，不能 issue/扩大授权。
- **消费幂等不等于 provider 可重放**：`消费ID=task_id:attempt` 在项目账本中只允许一行。首次 consume 原子写 `in_flight`；同 ID 重入或存在未完成 reservation 时一律 fail-closed，不会把账本 no-op 当成免费二次 submit。只有 provider 查询/恢复取得持久 completion evidence 后才能 `finalize`；runner 在 provider command、paid-boundary receipts、产物校验都通过后自动 finalize。崩溃在 consume 与 provider receipt 之间时必须先查原 submit/恢复，不能自动新建 attempt 绕过不确定扣费。
- **compose 按真实 effect 分流**：`BGM来源=无` 且 canonical master 尚不存在时，首次本地 ffmpeg 合成可 `needs_stage_execution` 自动继续；任何 working/未验收/已验收 canonical master 已存在、acceptance receipt 损坏或 canonical resolver 不可用，都视为不可逆覆盖风险并保留人工硬停。安全本地分支不创建 paid expectation、不消费 spend envelope，但产物、compose/review gate 与最终签收仍完整执行。
- **一个执行哈希**：授权里的 `execution` 同时绑定 resolved command、producer canonical input、submit/compiled request 和完整 producer contract。image 从真实 compiler 重算每个物理 target 的 paid input fingerprint + compiled request SHA；video 从唯一 prepared manifest 重算 batch fingerprint + 每个物理 clip submit snapshot。禁止回退到 episode prework cache、task 自报 hash 或“若干输入文件”的近似摘要。voice/compose 尚无可纯重算的 prepared producer manifest，因此当前 production 授权明确 fail-closed，待各 producer 提供 canonical contract 后才开放。
- **花钱点二次互锁**：runner 把每个物理 target 的批准 expectation 注入 producer；Codex/Dreamina image 与 video 在真正调用付费后端前现场重算 input fingerprint + submit request SHA，完全一致才执行，并原子写 paid-boundary receipt。出现任一 batch marker 却缺 expectation 必须 fatal；batch 只允许直接 producer argv 或仓库内 SHA/argv 精确识别的官方 image wrapper，shell 控制符、命令替换和任意外层 wrapper 均拒绝，不能通过清空环境绕过互锁。
- **认领即原子预留预算**：production task 在同一个 queue lock / SQLite `BEGIN IMMEDIATE` claim 临界区按本次 attempt 预留 estimate；第二个 worker 必须看到首个 reservation，不能并发穿透 runtime cap。真正开始命令后即使 exit 非 0/output/gate fail 也按 reported actual（没有则保守按 estimate）结算；只有明确 `execution_started=false` 的 preflight/config failure 才释放。lease 崩溃状态未知也保守结算，避免回收重跑造成双花。
- **一个完成定义**：可路由阶段只有在 runner 自身 `status=pass + exit_code=0`、命令确实越过执行边界、`output_contract + progress_columns` 校验通过、声明的 post gate 返回 `exit_code=0 && blocks=0` 后，才提交 `done`。queue 层按 stage contract 推导 hard completion，重新验证授权与 paid receipt，并在持有 queue 锁的提交瞬间逐个重算产物存在性、SHA 与解码状态；任何 verify→commit 漂移都转成 `qa_blocked + output_changed_before_commit`，已越过付费边界仍结算成本。终态 `n2d_batch_completion_commit.digest` 一次绑定 task/attempt、canonical content fingerprint、授权摘要、精确产物 SHA、`output_commit_attestation` 与 gate。review 额外只认 `_lib/acceptance_contract.py` 对当前母版/score/ledger/review-ui/release verdict 的 canonical 人工收据，并把 receipt id/evidence digest 纳入同一 commit；`needs_acceptance_signoff` 永远 human-only。缺收据时持久化已有 command/output/gate evidence，释放 lease并停在 `qa_blocked`；人工签收后再次 `mark pass` 原子 reconcile 为 done，不重跑 review 命令。gate BLOCK/异常进入非终态 `qa_blocked`，修复后显式 requeue，不计作完成。
- **runner mark 不依赖 telemetry 成功**：dashboard 记账失败只写入 `last_runner.telemetry_error`；产物校验与 post gate 已通过时仍可提交 `done`，避免纯观测故障制造重复付费。
- **dry-run 真只读**：`--dry-run` 只预览候选、canonical preflight 和命令；不 claim、不增加 attempts、不执行、不写 telemetry、不 mark。
- **失败按重试上限回队列**：`mark --status fail` 后，未超过 `max_retries` 变 `retry_queued`；超过后变 `failed`，需要人工处理。
- **失败必须可分类、可停线**：失败任务会写 `last_error_class`（preflight_block / capability / budget / timeout / output_contract / configuration / command_failed / unknown）。超过重试上限的任务会标 `dead_letter=true` 并进入 `dead_letter_queue.json/md`；死信不是“再试一次”，而是人工判定根因、修 wrapper/后端/素材/预算后再重新排队。
- **critical stop-loss 是执行互锁**：死信或 stop-loss 达 critical 后，spend probe、claim 与 consume 三个边界都会机器阻断；它不是动作卡上的提醒。清除根因并重建当前治理证据前，不得靠重启 worker 或换 attempt 继续花费。
- **任务带幂等键**：每个任务按作品根、集、stage、reason、scope、affected shots/artifacts 生成稳定 `idempotency_key`，runner 会注入 `N2D_IDEMPOTENCY_KEY` 并写进 dashboard trace。阶段 wrapper 能用它防重复提交、查重输出、或把同一次生产尝试串回发布/死信/账本。
- **预算按合并后账本裁剪**：`--budget` 会在默认合并既有队列后，对整个 ledger 重新计算预算；历史 `running/done/retry_queued` 任务占用预算，新的未开始任务超限时标 `blocked_budget`，不进入可 claim 批次。真实成本仍由 `n2d-dashboard` 在阶段完成后记录。
- **批量扩张看 ROI，不看“能跑完”**：runner 跑完一批后必须 `python3 skills/n2d/n2d-dashboard/scripts/dashboard.py build <作品根> --markdown`。继续扩量前看每分钟成本、每集耗时、一次通过率、重抽率、投放净回收/生产成本；若 ROI 不达标，先排返工/模板/路由优化任务，不盲目追加集数。
- **只重跑受影响范围**：定妆变更、gate finding、审片问题、asset impact 输出、验收总账 root cause、`n2d-identity` 跨集漂移报表都应转成 `--rerun-from` + `--affected-shot/--affected-artifact/--scope`，只排受影响镜头或 Clip，不整集无脑重跑。
- **P-3 排期可直接变队列**：`n2d-script` 的 P-3 gate 会把 `ai_shooting_schedule.json` 物化为 `生产数据/ai_shooting_schedule_batch_seed_第N集.json/md`。`queue.py plan --from-shooting-schedule` 消费它生成 image/video 任务，并把 `affected_shots` 注入阶段 scope；runner 仍按 `batch_runner.json` 的真实 stage 命令执行，不绕过各阶段 gate。
- **自动审片评分可直接入队**：`n2d-score --enqueue-low` 会把低分维度聚合成 `auto_return_tasks`，再写入本队列；batch 只负责承接和执行状态，不重新解释评分逻辑。
- **slash skill 不是 shell 命令**：队列里的 `n2d-image <root> 第1集` 是人/agent 可读建议。runner 要真正执行，必须在 `生产数据/batch_runner.json` 里给该 stage 配 shell 命令，或用 `--command` 临时覆盖。

## 批量放量准则（工业化口径）

n2d-batch 的价值不是“把所有集一口气跑完”，而是把多集生产变成**可控试产 → 小批量 → 放量**：

1. **先打样**：第 1 集必须完整跑通 `script → voice/native_av → image → video → compose → review/score → 验收签收`，并把 dashboard、score、consistency ledger、review-ui 产物都落档。
2. **再小批量**：先跑 2-10 集，观察 `n2d-dashboard` 的每分钟成本、每集耗时、一次通过率、重抽率、QA 阻断 Top、投放净回收/生产成本；`governance.py check` 会同步跑 `skills/n2d/scripts/stop_loss.py`，脸漂率、重抽率、每分钟成本、QC block 率、接缝失败率、口型失败率超过阈值即 critical 停线。**口径区分**：能停线的是 stop_loss 的**生产重抽率**（redraw 事件/生成尝试）；governance 自己的队列**任务重试率**（`max_retry_rate=0.35`）只 warn 不停线，两者别混。死信 >0 与 stop_loss critical 是仅有的两类停线信号；`max_running_age_sec` 超龄 running 任务记 warn 提示回收。
3. **按瓶颈扩量**：若脸漂/服装漂高，先修 identity/定妆/后端主体绑定；若视频重抽高，先修 model routing / motion control / 拆镜模板；若成本高，先调后端与 Clip 长度；若留存差，回 `n2d-feedback` 修开场/集尾/镜头密度。
4. **只排下一步和最小返工**：常规 plan 只排每集当前下一步；返工必须带 `--rerun-from`、`--scope`、`--affected-shot` 或 `--affected-artifact`，避免整集重跑吞成本。
5. **多机：共享 FS 用 atomic 锁，高并发再换协调后端（F3·2026-06-26）**：`N2D_QUEUE_LOCK` 选锁策略——`auto`（默认·有 fcntl 走 flock·零行为变化）/ `atomic`（O_EXCL 锁文件 + **陈旧锁自动接管**，治原 fallback「持锁机器死了→永久死锁」；O_EXCL create 在 NFSv3+ 原子，比 flock 跨 NFS 可靠）。**共享 FS 多机渲染农场**设 `N2D_QUEUE_LOCK=atomic`（陈旧阈值 `N2D_QUEUE_LOCK_TTL` 默认 120s）。worker id 已含 `hostname:pid` 天然带机器身份；真正的多机断点恢复靠**每任务 lease + reclaim_expired + heartbeat**（已有·一台机器死了它的任务自动回收）。**诚实边界**：这把锁只护临界区——高并发/强一致仍建议接 DB/Redis/对象存储条件写/消息队列，atomic 锁是「共享 FS 够用」不是「分布式强一致」。
6. **协调后端状态必须显式可见**：`queue.py coordination-status <作品根>` 会读取 `生产数据/coordination_backend.json`（没有则默认 `local_file`），并把后端/锁策略/风险写入 `batch_queue.json/md`。当前内置可执行后端：`local_file/shared_fs/sqlite`；`redis`、`db`、`object_store` 可先声明为外部后端意图，但没有 adapter 时状态是 `declared_not_active`，不能伪装成强一致。

## 常用命令（速查）

> 完整命令目录（stage 过滤 / worker 配置 + wrappers / findings 回流 / 复检指纹闭环 / 低分回流 / 预算自定义）见 `references/commands.md`；队列与账本字段 schema 见 `references/schema.md`。

```bash
# 1) 按 _进度.md 自动排队（每集只排「当前下一步」；默认合并不覆盖在跑队列，要整队替换加 --replace[ --force]）
python3 skills/n2d/n2d-batch/scripts/queue.py plan <作品根> --episodes 1-5 \
  --max-concurrency 2 --max-retries 1 --budget 40 --budget-unit work_units

# 1.1) 从 P-3 AI shooting schedule / batch seed 导入 image/video 队列任务
python3 skills/n2d/n2d-batch/scripts/queue.py plan <作品根> \
  --from-shooting-schedule <作品根>/生产数据/ai_shooting_schedule_batch_seed_第1集.json

# 2) 认领并发槽 / 手动标记结果
python3 skills/n2d/n2d-batch/scripts/queue.py claim <作品根> --limit 2
python3 skills/n2d/n2d-batch/scripts/queue.py mark <作品根> <task_id> --status pass|fail [--note "..."]

# 3) Worker 自动执行（命令配在 生产数据/batch_runner.json；默认验证契约产物并在 post gate 后提交 done）
python3 skills/n2d/n2d-batch/scripts/runner.py <作品根> --until-empty --limit 1

# 3.0) 只读预览：不认领、不执行、不改账本
python3 skills/n2d/n2d-batch/scripts/runner.py <作品根> --dry-run --limit 1

# 3.1) 执行前消费 run.py next 动作卡；遇 source/update/gate/image_qc/能力证据/合规/环境/选择点/验收证据阻断就不跑命令
python3 skills/n2d/n2d-batch/scripts/runner.py <作品根> --until-empty --limit 1 --next-preflight

# 3.2) v2 阶段预算包：issue 只能来自可审计的人审记录；probe/verify 不消费，runner 才 consume
python3 skills/n2d/_lib/spend_envelope.py issue <作品根> --stage image \
  --model "GPT Image 2" --channel "Codex CLI" --input-sha256 <当前canonical-sha256> \
  --scope-json '<精确scope-json>' --max-calls 8 --max-attempts 2 \
  --cost-ceiling 40 --currency work_units --approver '<责任人>' \
  --approval-reference '<审批记录ID/URL>' --source-quote '<人的原始批准语句>'
python3 skills/n2d/n2d-batch/scripts/spend_probe.py <作品根> 第1集 image --json

# 崩溃恢复后，仅在已有 provider completion receipt/query evidence 时关闭 in_flight；不会新增调用
python3 skills/n2d/_lib/spend_envelope.py finalize <作品根> \
  --envelope <预算包.json> --consumption-id <task:attempt> \
  --evidence-json '{"kind":"n2d_provider_recovery_evidence","provider_submit_id":"...","provider_status":"success","query_receipt_reference":"...","query_response_sha256":"sha256:..."}'

# 4) 单机多 worker 安全：稳定 worker id + 租约 + 断点恢复（多机/私有算力池需换协调后端，非本锁）
python3 skills/n2d/n2d-batch/scripts/runner.py <作品根> --until-empty --worker w1 --lease-seconds 1800
python3 skills/n2d/n2d-batch/scripts/runner.py <作品根> --until-empty --worker w1 --resume   # 崩溃重启自愈
python3 skills/n2d/n2d-batch/scripts/queue.py reclaim <作品根>                               # 回收过期租约
python3 skills/n2d/n2d-batch/scripts/queue.py heartbeat <作品根> <task_id> --worker w1       # 长任务续租 lease
python3 skills/n2d/n2d-batch/scripts/queue.py coordination-status <作品根>                   # 查看账本协调后端与锁策略
python3 skills/n2d/n2d-batch/scripts/queue.py sqlite-doctor <作品根> --write                 # SQLite DB ↔ JSON mirror 一致性体检
python3 skills/n2d/n2d-batch/scripts/queue.py job-receipt <作品根> --task-id 001-image-progress --status succeeded --external-job-id <job>
python3 skills/n2d/n2d-batch/scripts/queue.py reconcile-jobs <作品根> --apply                # 外部 job receipt 对账，补断链 pass/fail

# 5) 只重跑受影响镜头（不整集重来；reason=rerun，不因该集已完成被跳过）
python3 skills/n2d/n2d-batch/scripts/queue.py plan <作品根> --episodes 2 --rerun-from image \
  --affected-shot Clip_03 --affected-artifact 出图/第2集/图片/Clip_03.png --scope "定妆_王敦更新"

# 6) findings / ledger / 低分回流 + 闭环复检（修复→resolved / 复发→reopen）
python3 skills/n2d/n2d-batch/scripts/queue.py plan <作品根> --from-consistency-findings <findings.json>
python3 skills/n2d/n2d-batch/scripts/queue.py plan <作品根> --from-consistency-ledger <作品根>/生产数据/consistency_ledger_第1集.json
python3 skills/n2d/n2d-batch/scripts/queue.py plan <作品根> --from-events   # production_events.jsonl 里未被后续 pass 承接的 generation/redraw fail → 重试任务（手动/外部生成失败也进闭环）
python3 skills/n2d/n2d-score/scripts/score.py <作品根> 第1集 --run-checks --threshold 85 --enqueue-low
python3 skills/n2d/n2d-batch/scripts/runner.py <作品根> --until-empty --recheck   # pass 后自动刷门禁再判现状

# 7) 生产治理：初始化 SLO、检查死信/重试率/阶段耗时/stop-loss，必要时停线
python3 skills/n2d/n2d-batch/scripts/governance.py init-slo <作品根>
python3 skills/n2d/n2d-batch/scripts/governance.py check <作品根> --write
python3 skills/n2d/n2d-batch/scripts/governance.py dead-letter <作品根> --write
python3 skills/n2d/scripts/stop_loss.py <作品根> --write --json
```

## 与 n2d-dashboard 的关系

- `n2d-batch` 管“排什么、谁在跑、失败是否重试、预算是否挡住”。
- `n2d-dashboard` 管“实际花了多少、耗时多少、重抽原因、QA 阻断、通过率”。
- `n2d-score` 管“每集机器分、低分维度、应回流哪个 stage”。
- `n2d-identity` 管“哪个角色/形态从哪一集开始漂、哪个后端 adapter 未 ready”，漂移回流通常转成 `--rerun-from image` 或 `--rerun-from video` 的受影响镜头任务。

队列任务完成后，执行的阶段 skill 仍应按各自 SKILL.md 调 `n2d-dashboard record/gate` 记录真实生成成本和 QA。runner 只补“worker 执行耗时/exit_code” telemetry，不替代阶段内部的成本、重抽、QA 记录。不要用 batch 的估算成本替代 dashboard 的真实成本。

## 生产治理 / 停线

`governance.py` 是批量放量后的停线入口，不替代 dashboard ROI，但负责队列健康和 stop-loss：

- `production_slo.json`：项目级 SLO（最大死信数、最大重试率、各 stage 最大耗时和最大尝试次数）。
- `stop_loss`：从 `production_events.jsonl`、dashboard、findings/ledger 聚合脸漂率、重抽率、每分钟成本、QC block 率、接缝失败率、口型失败率；超过阈值 critical，先停线回合同层修。
- `batch_governance.json/md`：当前队列是否 pass/warn/critical。
- `dead_letter_queue.json/md`：超过重试上限或最终 failed 的任务，带 `error_class`、`note`、`idempotency_key`。

`governance.py check` 有 critical 时退出码为 1，适合 cron/CI/agent runner 停线；死信出现后先修根因，再用 `queue.py plan --rerun-from ...` 重新排最小范围任务。

## 常见错误

| 错误 | 纠正 |
|---|---|
| 让 runner 直接重写阶段逻辑 | 不做。runner 只调配置好的阶段命令；阶段规则仍归对应 n2d skill |
| batch 跑过单集编排器的硬阻断 | runner 默认消费 `run.py next`；`voice/image/video/compose` 无视关闭配置，必须匹配当前同集 frontier，且只接受 `needs_payment_confirm +` 任务绑定授权。`done/prework_failed/needs_stage_execution`、entry/gate/image_qc/compliance/choice/验收阻断一律不执行。`--no-next-preflight` 只影响非生产工具任务 |
| 把 queued 或 batch_runner 命令当付费授权 | 在 `batch_runner.json.production_authorizations[task_id]` 写 canonical 收据：除审批、scope、model/channel、ceiling/expiry 外还必须带 `execution.command_digest/input_fingerprint/submit_request_digest/producer_contract_digest`；不得用通配、task 自报 hash 或复制旧授权 |
| 用 episode/prework fingerprint 冒充生产请求 | 不允许。image/video 必须由 stage producer resolver 重算物理 target/clip 的 canonical contract；voice/compose 在 producer 尚无 prepared contract 时 fail-closed |
| 命令 exit 0 就手工 mark pass | 生产任务的 `queue.py mark --status pass` 会拒绝缺少 output verification 与 post gate evidence 的提交；由 runner 完成 canonical commit |
| gate 失败后任务却是 done | 不允许；应为 `qa_blocked`。修复门禁根因后显式 `queue.py mark ... --status queued` 再跑 |
| review 命令/普通 gate 通过就自动验收 | 不允许。`needs_acceptance_signoff` 阻断 batch；review done 只消费 `_lib/acceptance_contract.py check` 的 canonical 人工收据，缺 progress 行/验收列也 fail-closed。缺收据时是 `qa_blocked` 等待态，签收后 `mark pass` 复用持久化 evidence，不重跑命令 |
| 两 worker 各看 planning budget 后同时花钱 | claim 临界区按 attempt 原子 reserve；看 `batch_queue.json.budget.runtime_reserved_total/runtime_settled_total/runtime_available`，超 cap 的任务转 `blocked_budget` |
| 直接跑队列里的 `n2d-image` slash command | slash command 不是 shell 命令；在 `batch_runner.json` 配真实 shell 命令 |
| 多个 agent 口头分任务 | 统一 `claim`（已上 flock 原子认领），否则并发槽和状态会乱 |
| 多 worker 不给 `--worker` id | 给稳定 id；否则 `--resume` 无法回收"自己"上次残留的 running |
| worker 崩了任务卡 running | 等租约过期自动回收，或跑 `queue.py reclaim`；重启用 `--resume` 立即自愈 |
| 把单机 flock 当多机分布式锁 | flock 跨 NFS 不可靠；多机/私有算力池要换协调后端，别靠本锁 |
| 失败后手动再跑但不 mark | 必须 `mark --status fail`，让重试进入账本 |
| 定妆改了就整集重出 | 用 `--rerun-from image --affected-shot/--affected-artifact` 只排受影响镜头 |
| 预算只看预估不看实际 | 预估只挡任务；真实成本以 `n2d-dashboard` 为准 |
