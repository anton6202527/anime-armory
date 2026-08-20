# n2d-batch 命令目录（完整用法）


> SKILL.md 只留常用命令速查；本文件是完整命令目录（排队/过滤/认领/worker/多worker 安全/findings 回流/复检/低分回流/预算）。队列与账本字段 schema 见 `schema.md`。

## 标准命令

### 1. 按 `_进度.md` 自动排队

```bash
python3 skills/n2d/n2d-batch/scripts/queue.py plan <作品根> \
  --episodes 1-5 \
  --max-concurrency 2 \
  --max-retries 1 \
  --budget 40 \
  --budget-unit work_units
```

输出：

- `生产数据/batch_queue.json`
- `生产数据/batch_queue.md`

默认会为每集只排“当前下一步”。例如第1集卡 `配音` 就排 `voice`，第2集卡 `出图` 就排 `image`。

默认写入时会**合并**到既有 `batch_queue.json`，不覆盖在跑任务；合并后会按完整 ledger 重新计算预算，而不是只看本次新增计划。若确实要丢弃旧队列：

```bash
python3 skills/n2d/n2d-batch/scripts/queue.py plan <作品根> --episodes 1-5 --replace
python3 skills/n2d/n2d-batch/scripts/queue.py plan <作品根> --episodes 1-5 --replace --force  # 队列有 running 时才允许强替换
```

### 2. 按 stage 过滤

```bash
python3 skills/n2d/n2d-batch/scripts/queue.py plan <作品根> --stage image --episodes 1-20
python3 skills/n2d/n2d-batch/scripts/queue.py plan <作品根> --stage n2d-video --episodes 8-12
```

`--stage` 接受 stage key、owner、label、进度列名：如 `image` / `n2d-image` / `出图`。

### 3. claim 并发槽

```bash
python3 skills/n2d/n2d-batch/scripts/queue.py claim <作品根> --limit 2
```

返回可执行任务。执行者按任务里的 `owner` 和 `command` 去调对应 skill。完成后必须 `mark`。

### 4. Worker 自动执行

先配置 runner 命令：

```json
{
  "commands": {
    "voice": "python3 skills/n2d/n2d-voice/render_voice.py \"{root}\" \"{ep}\" zh",
    "image": "bash skills/n2d/n2d-batch/scripts/run_n2d_image.sh \"{root}\" \"{ep}\"",
    "video": "N2D_VIDEO_RANGE=06-10 bash skills/n2d/n2d-batch/scripts/run_n2d_video.sh \"{root}\" \"{ep}\"",
    "compose": "bash skills/n2d/n2d-batch/scripts/run_n2d_compose.sh \"{root}\" \"{ep}\" zh",
    "review": "bash skills/n2d/n2d-batch/scripts/run_n2d_review.sh \"{root}\" \"{ep}\""
  },
  "env": {
    "NO_PROXY": "127.0.0.1,localhost",
    "N2D_IMAGE_COMMAND": "python3 my_image_runner.py \"$N2D_ROOT\" \"$N2D_EPISODE\""
  }
}
```

保存到：

```text
创作区/制漫剧/<剧名>/生产数据/batch_runner.json
```

执行一轮：

```bash
python3 skills/n2d/n2d-batch/scripts/runner.py <作品根> --limit 1
```

持续跑到队列无可 claim 任务：

```bash
python3 skills/n2d/n2d-batch/scripts/runner.py <作品根> --until-empty --limit 1 --timeout-sec 3600
```

runner 默认会在执行前消费 `n2d/run.py next`。`voice/image/video/compose` 始终强制 canonical preflight：任务集与 `frontier.ep/stage_key` 必须完全一致，动作卡必须是 `needs_payment_confirm`，并有任务绑定授权；`next_preflight=false` / `--no-next-preflight` 只影响非生产工具任务。授权检查前还会解析最终命令并从实际 producer 重算请求，不接受 task/config 自报的输入 hash。

产物与 `_进度.md` 后置条件默认验证；保留下面的参数用于强调：

```bash
python3 skills/n2d/n2d-batch/scripts/runner.py <作品根> --until-empty --verify-outputs
```

`--verify-outputs` 会读取 `n2d/_lib/n2d_contract.py` 的 `output_contract`：普通阶段按 required outputs 校验；配音/合成成片等存在合法替代产物的阶段按 `any_of` 组合校验，避免真实配音与占位清单、中文成片与双语成片互相误判。

`--no-verify-outputs` 只对非生产工具任务生效；`voice/image/video/compose` 不能跳过。只读预览使用：

```bash
python3 skills/n2d/n2d-batch/scripts/runner.py <作品根> --dry-run --limit 1
```

它不会 claim、增加 attempts、执行命令、写 telemetry 或 mark。

runner 行为：

1. 生产任务先解析最终命令，从 stage producer 重算 canonical input/submit contract，再核对 canonical frontier 并消费与两者绑定的授权；仅 queued 不算授权。
2. `claim` 可执行任务，尊重 `max_concurrency`；production task 在同一锁/事务内原子 reserve estimate，超 runtime cap 则转 `blocked_budget`。
3. 执行 `batch_runner.json.commands[stage_key]` 或 `commands[owner]`。
4. exit code `0` 后强制验证 output contract/progress，再运行声明的 post gate。
5. 两者均通过 → 携 completion evidence `mark pass` → `done`；gate BLOCK/异常 → `qa_blocked`；命令/产物失败 → `retry_queued` 或 `failed`。命令一旦开始，非零退出、产物失败和 gate block 都可能已花费，按 actual（缺失时按 estimate）结算；只有明确未执行的 preflight/config failure 释放 reservation。
6. 写 `n2d-dashboard` 最终 runner event；telemetry 故障不改变已经由产物+gate 证明的完成结论。

命令模板可用变量：`{root}`、`{episode}`/`{ep}`、`{task_id}`、`{stage_key}`、`{owner}`、`{reason}`、`{scope}`、`{affected_shots}`、`{affected_artifacts}`。runner 同时注入环境变量 `N2D_ROOT`、`N2D_EPISODE`、`N2D_TASK_ID`、`N2D_STAGE` 等。

仓库已提供标准 wrapper：

- `skills/n2d/n2d-batch/scripts/run_n2d_script_stage2.sh`：刷新分镜定稿、字幕/镜头时长、逐镜意图、导演运镜、锚帧、伏笔/剧情/节拍/前因/奇观/风险审计、事实合同；只跑确定性文本/账本步骤，不出图、不出视频、不消耗积分。
- `skills/n2d/n2d-batch/scripts/run_n2d_image.sh`：先跑 image_preflight gate；实际生图命令必须由 `N2D_IMAGE_COMMAND` 显式配置，避免 wrapper 猜后端或误花钱。
- `skills/n2d/n2d-batch/scripts/run_n2d_video.sh`：只用于先跑 identity/router、共享视频物化、video_preflight 与 `prepare`，生成稳定 manifest。不要在同一条获批命令里再设 `N2D_VIDEO_SUBMIT_ONE/AUTO_SUBMIT`：prepare 会在授权 hash 后改变输入，batch 将 fail-closed。应先 prepare，再为精确 manifest + physical clip 的 `video_runner.py submit` 命令单独审批。
- `skills/n2d/n2d-batch/scripts/run_n2d_compose.sh`：先刷新 `mouth_visible` sidecar、物化共享视频，再跑 compose gate，最后调用 `n2d-compose/compose.sh`。
- `skills/n2d/n2d-batch/scripts/run_n2d_review.sh`：刷新高动态成片证据、motion reference、review gate、score、consistency ledger 和 review-ui；通过后仍只生成验收证据，不自动回写 `验收=✅`。

示例配置可直接复制为项目级文件后再按后端补 env：

```bash
cp skills/n2d/n2d-batch/references/batch_runner.example.json <作品根>/生产数据/batch_runner.json
```

> **stage 前置边界**：runner 不内置 image/video/compose 的业务规则，避免把阶段逻辑复制进队列层；标准 wrapper 只做可复用 gate/preflight，真正的生成仍由对应阶段脚本或显式配置的本地命令执行。

### 4.1 幂等键 / trace / 错误分类

每个任务会按作品根、集、stage、reason、scope、affected shots/artifacts 生成稳定 `idempotency_key`。runner 自动注入：

```text
N2D_IDEMPOTENCY_KEY
```

并把 `task_id / trace_id / idempotency_key / error_class` 写入 dashboard manual event 的 `meta`，由 dashboard 提升到 `event.trace`。阶段 wrapper 可用该键避免重复提交同一付费任务，或把生成产物、死信和发布 manifest 串回同一次生产尝试。

失败会写 `last_error_class`：`preflight_block / capability / budget / timeout / output_contract / configuration / command_failed / unknown`。超过重试上限后任务标 `dead_letter=true`，等待人工处理根因。

### 4.2 Canonical production authorization

`voice/image/video/compose` 每个 task 都要有独立授权收据，放在 `batch_runner.json.production_authorizations[task_id]` 或 task 的 `production_authorization`。收据至少包含：

```text
version / approval_id / decision / approver / issued_at / expires_at
task_id / idempotency_key / task_digest / attempt / stage_key / episode / scope
model / channel / ceiling.amount / ceiling.currency / authorization_digest
execution.command_digest / execution.input_fingerprint
execution.submit_request_digest / execution.producer_contract_digest
```

审批面应调用 `runner.make_production_authorization(task, root=..., resolved_command=..., config=..., ...)` 或实现完全相同的 canonical JSON 摘要算法，不要手填 digest。`task_digest` 绑定 task 内容、估算成本与 `execution`；`attempt` 让收据只能消费一次，付费失败后的 retry 必须重新审批；`authorization_digest` 绑定整张收据并提供 canonical tamper-evident checksum。`approver` 必须能追责；expiry 必须带时区且未过期；model/channel 必须显式声明，无法预知时可用 `any`；estimate 必须与 ceiling 同币种/单位且不超过上限。task、scope、idempotency、最终命令、producer 输入/请求、model/channel 或成本变化后，旧收据立即失配，必须重新审批。

这张 SHA-256 收据提供 canonical 防篡改绑定，不把配置 presence 当审批人身份，也不等价于远端数字签名；真实 approver 仍是必填审计主体。

producer contract 的当前支持边界：

- image：只接受真实 `codex_image_runner.py` / `dreamina_image_runner.py`，按物理 target 重算 compiler paid input fingerprint 与 compiled request SHA；prompt、引用图、registry、设置或实际 model/channel 改动都会让旧授权失效。
- video：只接受唯一且未过期的 prepared manifest，以及显式 physical clip；按 manifest fingerprint 与 submit snapshot 重算。prompt、首尾帧、duration、adapter registry 或 manifest/clip 改动都会失效。显式 range 对应 manifest 缺失时不回退到别的批。
- voice / compose：producer 目前没有可纯重算、可在执行边界消费的 prepared request manifest；batch 不会拿 episode prework cache 或泛化文件摘要代替，production 授权暂时 fail-closed。

### 4.5 单机多 worker 安全（原子认领 + 租约回收 + 断点恢复）

一台机器多 GPU / 多 worker 同抢一个队列时，靠**文件锁 + 租约**保证安全，**纯本地、零后端**（多机/私有算力池需协调后端，见下「边界」）：

```bash
# 各 worker 起一个、给稳定 id；任务认领后打 lease，执行期自动心跳续租
python3 skills/n2d/n2d-batch/scripts/runner.py <作品根> --until-empty --worker w1 --lease-seconds 1800
python3 skills/n2d/n2d-batch/scripts/runner.py <作品根> --until-empty --worker w2 --lease-seconds 1800
# 某 worker 崩了重启 → --resume 先回收自己上次残留的 running，再继续认领（断点恢复）
python3 skills/n2d/n2d-batch/scripts/runner.py <作品根> --until-empty --worker w1 --resume
# 手动回收过期租约（任意 worker 死了没 mark，租约到点即可被别的 worker 接走）
python3 skills/n2d/n2d-batch/scripts/queue.py reclaim <作品根>
```

- **原子认领**：`claim/mark/reclaim/renew` 全在 `生产数据/batch_queue.lock` 的 `flock` 互斥锁内"重读最新队列 → 改 → 原子写(temp+`os.replace`)"。多进程同抢**绝不双认领、绝不互相覆盖**。
- **原子预算预留**：production task 的 estimate 在同一 claim 临界区写入 `budget_reservation`；SQLite 后端位于同一个 `BEGIN IMMEDIATE` 事务。第二个 worker 在判断 cap 时一定能看到第一个 reservation。结算后写入 `budget_charges`，并刷新 `budget.runtime_reserved_total/runtime_settled_total/runtime_available`。
- **租约 lease**：认领即给任务 `lease_until`，runner 执行期起心跳线程按 `lease/3` 续租；崩溃后租约不再续 → 到点过期。
- **断点恢复**：`claim` 每次认领前自动回收过期租约的 running → `retry_queued`（或超重试上限 → `failed`）。`--resume` 额外强制回收**本 worker** 残留的 running（需稳定 `--worker` id）。崩溃状态无法证明命令未越过付费边界，因此 production reservation 会保守按 estimate settle，防止回收重跑造成双花。
- **runner 不再持 stale 队列**：跑任务时不持锁，认领/标记各自锁内重读最新队列——修掉了"长任务跑完后回写整队、覆盖别的 worker 认领"的老 bug。
- **边界**：`flock` 只在**单机/本地文件系统**可靠；跨 NFS 不可靠。**多机/私有算力池**要换真正的协调后端（DB/Redis/对象存储条件写/消息队列）或单 dispatcher 拉取模型——本锁不负责跨主机。

### 5. 手动标记结果与失败重试

```bash
python3 skills/n2d/n2d-batch/scripts/queue.py mark <作品根> 002-image-progress --status fail --note "脸漂移，需重抽"
python3 skills/n2d/n2d-batch/scripts/queue.py mark <作品根> 002-image-progress --status queued --note "根因已修，重新排队"
```

失败未超过重试上限时会回到 `retry_queued`；超过后变 `failed`。不要用 CLI 手工把 hard stage 标成 pass：缺 runner 的 output verification / post gate completion evidence 会 fail-closed。review 即使命令和普通 gate 都通过，也必须等 `_lib/acceptance_contract.py` 校验当前母版、score、ledger、review-ui、release verdict 所绑定的 canonical 人工收据；`needs_acceptance_signoff` 永远只交给人处理。此时 runner 会保存已通过的 command/output/post-gate evidence、释放 lease，并将任务置为 `qa_blocked`（`completion_block_reason=needs_acceptance_signoff`）；人工签收后再次执行 `queue.py mark ... --status pass` 即可原子 reconcile done，不会重跑 review 命令。

### 5.5 生产治理 / SLO / 死信

```bash
python3 skills/n2d/n2d-batch/scripts/governance.py init-slo <作品根>
python3 skills/n2d/n2d-batch/scripts/governance.py check <作品根> --write
python3 skills/n2d/n2d-batch/scripts/governance.py dead-letter <作品根> --write
```

输出：

- `生产数据/production_slo.json`
- `生产数据/batch_governance.json`
- `生产数据/batch_governance.md`
- `生产数据/dead_letter_queue.json`
- `生产数据/dead_letter_queue.md`

`check` 有 critical 时退出码 1；`dead-letter` 有死信时退出码 1。量产 runner/cron/CI 应把这两个非零退出码视为停线信号：先修 wrapper、后端能力、预算或产物契约，再用最小范围 `plan --rerun-from ...` 重新排队。

### 6. 只重跑受影响镜头/Clip

```bash
python3 skills/n2d/n2d-batch/scripts/queue.py plan <作品根> \
  --episodes 2 \
  --rerun-from image \
  --scope "只重跑 Clip_03 首帧，因定妆_王敦更新" \
  --affected-shot Clip_03 \
  --affected-artifact 出图/第2集/图片/Clip_03.png \
  --max-concurrency 1 \
  --max-retries 2
```

这类任务 `reason=rerun`，不会因为该集 `_进度.md` 已显示完成而被跳过。

### 7. 承接一致性 / 人审 findings 回流

`n2d-review/scripts/consistency_audit.py` 会生成 `生产数据/consistency_findings_第N集.json`；`n2d-review-ui/scripts/review_ui.py --export-findings` 会生成 `生产数据/review_ui_findings_第N集.json`；`n2d-dashboard/scripts/dashboard.py gate ...` 会生成 `生产数据/gate_findings_<stage>_第N集.json`；`n2d-identity/scripts/voice_print_consistency.py` 会生成 `生产数据/consistency_findings_voice_print_第N集.json`。这些都是 `kind=n2d_consistency_findings`，可直接转成最小范围返工队列：

```bash
python3 skills/n2d/n2d-batch/scripts/queue.py plan <作品根> \
  --from-consistency-findings <作品根>/生产数据/review_ui_findings_第N集.json \
  --max-concurrency 1 \
  --max-retries 2
```

报告里带 `auto_return_tasks` 时优先按它排队；否则按 `(episode, return_to_stage, dim)` 聚合红黄 findings，并携带 `affected_shots` / `affected_artifacts`，避免整集重来。

**闭环复检（修复→标 resolved / 复发→reopen）**：每个返工任务带 `finding_fingerprints`（`(集×阶段×维度×最小定位)` 指纹，单一真值源 `n2d_contract.finding_fingerprint`；无镜头/产物定位时退回旧粒度）外加 `coarse_fingerprints`（`(集×阶段×维度)` 粗指纹，供回退匹配）。定位串先过 `canonical_scope_key` 归一：`Clip_03`、`Clip_03_首帧`、`镜头3`、`出图/.../Clip_03.png` 都归到同一 `clip_3`——同一镜头换写法/帧位/产物路径不再产生不同指纹，堵掉"定位粒度漂移导致已修问题被误判 resolved"。同一未解决问题**不随复审堆叠**——重排时同指纹的已结束任务 reopen、在途的跳过，而不是生成 `-2/-3` 重复任务。

**返工完成前门禁自动重跑**：命令与产物校验通过、任务有 `gate_stage` 时，runner 先重跑该 stage 的 `dashboard.py gate` 刷新 `gate_findings_*.json`，再决定是否提交 done。BLOCK/异常进入 `qa_blocked`，绝不先完成后补 gate。`--no-gate`（或 `batch_runner.json` 里 `"auto_gate": false`）只可关闭非生产工具任务的自动 gate；生产阶段声明的 gate 不可关闭。

```bash
# 复检：用最新 consistency_findings/review_ui_findings 的指纹回写队列
python3 skills/n2d/n2d-batch/scripts/queue.py recheck <作品根> [--episodes 1-5]
# 或让 runner 跑完自动复检（pass 后已自动刷新门禁 findings，--recheck 即对现状判定）
python3 skills/n2d/n2d-batch/scripts/runner.py <作品根> --until-empty --recheck
# 粗粒度回退：精确指纹对不上但该(集×阶段×维度)桶仍有问题则不判 resolved 而 reopen，堵漏放
python3 skills/n2d/n2d-batch/scripts/queue.py recheck <作品根> --coarse
python3 skills/n2d/n2d-batch/scripts/runner.py <作品根> --until-empty --recheck --coarse-recheck
```

复检把指纹已从最新审查消失的 done 任务标 `resolved=true`（留痕，不静默覆盖），仍在的 reopen 回 `queued`——这样"发现→返工→修复→复检确认不复现"才真正闭环，而不是只入队不回收。`--coarse` 是安全网：精确指纹归一后仍对不上（定位串大改/换成无镜头号的自由文本）但同 `(集×阶段×维度)` 桶仍有 findings 时，宁可 reopen 复核也不漏放（代价：同桶若有别的镜头未修，已修镜头会被一起召回，计入 `reopened_coarse`）。

### 8. 承接 n2d-score 低分回流

```bash
python3 skills/n2d/n2d-score/scripts/score.py <作品根> 第1集 \
  --run-checks \
  --threshold 85 \
  --enqueue-low \
  --max-concurrency 1 \
  --max-retries 1
```

`n2d-score` 会按七维低分自动生成 rerun 任务：角色/服装/场景/风格问题通常回 `image`，字幕/节奏回 `script_stage2`，音画同步回 `compose`。如果证据里能定位到 Clip 或产物路径，会写入 `affected_shots` / `affected_artifacts`，本 skill 随后按普通队列流程 `claim` / `mark` 即可。

## 预算估算

默认估算单位是 `work_units`。它先用于排队裁剪，production claim 时还会在锁/事务内成为 runtime reservation；实际成本仍应由阶段/runner 上报并由 `n2d-dashboard` 记录。queue 的 runtime 账本解决并发 cap，不取代 dashboard 的业务成本分析。

如需项目自定义成本表，写：

```json
{
  "image": {"amount": 3.0, "unit": "credits"},
  "video": {"amount": 12.0, "unit": "credits"},
  "voice": {"amount": 1.0, "unit": "credits"},
  "compose": {"amount": 0.5, "unit": "credits"}
}
```

保存到：

```text
创作区/制漫剧/<剧名>/生产数据/stage_cost_estimates.json
```

再用：

```bash
python3 skills/n2d/n2d-batch/scripts/queue.py plan <作品根> --budget 60 --budget-unit credits
```

运行时可检查 `batch_queue.json.budget`：

```text
runtime_reserved_total / runtime_settled_total / runtime_available / runtime_status
```

预算结算遵循付费边界：命令开始后，无论 exit 非零、output verify 失败还是 post gate block，都优先结算 reported actual，缺失时保守结算 reservation estimate；只有结构化 runner receipt 明确写出 `execution_started=false`，且错误属于 preflight/configuration，才释放 reservation。超 cap、单位不一致或实际成本超过授权 ceiling 会阻断 canonical completion，不会静默标 done。
