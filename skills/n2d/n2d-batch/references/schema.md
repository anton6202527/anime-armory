# n2d-batch schema

## Queue file

Path:

```text
创作区/制漫剧/<剧名>/生产数据/batch_queue.json
```

Shape:

```json
{
  "kind": "n2d_batch_queue",
  "version": 1,
  "root": "创作区/制漫剧/剧名",
  "generated_at": "2026-06-08T12:00:00+00:00",
  "updated_at": "2026-06-08T12:05:00+00:00",
  "max_concurrency": 2,
  "max_retries": 1,
  "budget": {
    "limit": 40,
    "unit": "work_units",
    "estimated_total": 28,
    "accepted_total": 28,
    "blocked_tasks": 0,
    "runtime_reserved_total": 3,
    "runtime_settled_total": 12,
    "runtime_available": 25,
    "runtime_unit": "work_units",
    "runtime_status": "ok",
    "runtime_updated_at": "2026-06-08T12:05:00+00:00"
  },
  "summary": {
    "total": 3,
    "by_status": {
      "queued": 3
    },
    "by_stage": {
      "voice": 1,
      "image": 1,
      "video": 1
    }
  },
  "batches": [
    ["001-voice-progress", "002-image-progress"],
    ["003-video-progress"]
  ],
  "tasks": []
}
```

## Task

```json
{
  "id": "002-image-progress",
  "episode": "第2集",
  "stage_key": "image",
  "stage_label": "出图",
  "owner": "n2d-image",
  "command": "n2d-image 创作区/制漫剧/剧名 第2集",
  "gate_stage": "image",
  "idempotency_key": "n2d:...",
  "status": "queued",
  "attempts": 0,
  "max_retries": 1,
  "priority": 2,
  "reason": "progress",
  "estimated_cost": {
    "amount": 3,
    "unit": "work_units"
  },
  "rerun_scope": "",
  "affected_artifacts": [],
  "affected_shots": [],
  "finding_fingerprints": [],
  "coarse_fingerprints": [],
  "budget_reservation": {
    "status": "reserved",
    "amount": 3,
    "unit": "work_units",
    "attempt": 1,
    "worker": "worker-1",
    "reserved_at": "2026-06-08T12:05:00+00:00"
  },
  "budget_charges": [],
  "last_error_class": "",
  "dead_letter": false,
  "dead_letter_at": "",
  "history": []
}
```

- `finding_fingerprints`：`(集×阶段×维度×最小定位)` 精确指纹（定位串过 `canonical_scope_key` 归一，同镜头不同写法/帧位/产物路径同指纹）；复检判 resolved/reopen + 防复审堆叠。
- `coarse_fingerprints`：`(集×阶段×维度)` 粗指纹；`recheck --coarse` 回退匹配用——精确指纹对不上但该桶仍有问题时不误判 resolved。
- `idempotency_key`：按作品根、集、stage、reason、rerun scope、affected shots/artifacts 生成的稳定键；runner 注入 `N2D_IDEMPOTENCY_KEY` 并写入 dashboard trace。
- `budget_reservation`：production task 在 claim 的同一个文件锁 / SQLite 事务里，按 `task + attempt` 原子预留估算成本。只有 `status=reserved` 的记录占用 runtime cap。
- `budget_charges`：完成一次付费尝试后的不可变结算条目。优先记录 runner 上报的 actual；没有可信 actual 时按 reservation estimate 保守结算。
- `last_error_class`：失败分类，取值建议为 `preflight_block / capability / budget / timeout / output_contract / configuration / command_failed / unknown`。
- `dead_letter` / `dead_letter_at`：超过 `max_retries` 或最终 failed 后写入；由 `governance.py dead-letter` 汇总给人工处理。

## Status values

| Status | Meaning |
|---|---|
| `queued` | Ready to claim |
| `running` | Claimed by a worker/agent |
| `retry_queued` | Failed but still within retry limit |
| `qa_blocked` | Command/output may exist, but post gate failed/could not run, or review is waiting for canonical human acceptance. Non-terminal; gate failures are requeued after repair, while acceptance waiting is reconciled by `mark pass` after signing without rerunning the command |
| `done` | Completed |
| `failed` | Failed after retry limit |
| `blocked_budget` | Not claimable because budget cap or unit mismatch blocks it |
| `cancelled` | Manually cancelled |

## Planning modes

| Mode | Trigger | Reason |
|---|---|---|
| Progress plan | `plan <root>` | `progress` |
| Targeted rerun | `plan <root> --rerun-from <stage> --episodes ...` | `rerun` |

Progress plan reads `_进度.md` and creates one task per selected episode's current next stage. Targeted rerun ignores the progress cell and creates tasks for the requested stage and affected scope.

## Runner config

Path:

```text
创作区/制漫剧/<剧名>/生产数据/batch_runner.json
```

Shape:

```json
{
  "commands": {
    "voice": "python3 skills/n2d/n2d-voice/render_voice.py \"{root}\" \"{episode}\" zh",
    "image": "bash skills/n2d/n2d-batch/scripts/run_n2d_image.sh \"{root}\" \"{episode}\"",
    "video": "N2D_VIDEO_RANGE=06-10 bash skills/n2d/n2d-batch/scripts/run_n2d_video.sh \"{root}\" \"{episode}\"",
    "compose": "bash skills/n2d/n2d-batch/scripts/run_n2d_compose.sh \"{root}\" \"{episode}\" zh",
    "review": "bash skills/n2d/n2d-batch/scripts/run_n2d_review.sh \"{root}\" \"{episode}\"",
    "*": "bash scripts/run_stage.sh \"{stage_key}\" \"{root}\" \"{episode}\""
  },
  "env": {
    "NO_PROXY": "127.0.0.1,localhost",
    "N2D_IMAGE_COMMAND": "python3 skills/n2d/n2d-image/scripts/codex_image_runner.py \"$N2D_ROOT\" \"$N2D_EPISODE\" --shots \"$N2D_AFFECTED_SHOTS\""
  },
  "production_authorizations": {
    "002-image-progress": {
      "version": 1,
      "approval_id": "approval-20260820-001",
      "decision": "approved",
      "approver": "producer@example.com",
      "issued_at": "2026-08-20T10:00:00+08:00",
      "expires_at": "2026-08-20T11:00:00+08:00",
      "task_id": "002-image-progress",
      "idempotency_key": "n2d:...",
      "task_digest": "sha256:<canonical-task-digest>",
      "attempt": 1,
      "stage_key": "image",
      "episode": "第2集",
      "scope": {
        "rerun_scope": "",
        "affected_shots": [],
        "affected_artifacts": []
      },
      "execution": {
        "command_digest": "sha256:<resolved-command-digest>",
        "input_fingerprint": "sha256:<canonical-producer-input-digest>",
        "submit_request_digest": "sha256:<canonical-submit-or-compiled-request-digest>",
        "producer_contract_digest": "sha256:<complete-producer-contract-digest>"
      },
      "model": "any",
      "channel": "any",
      "ceiling": {
        "amount": 3,
        "currency": "work_units"
      },
      "authorization_digest": "sha256:<canonical-authorization-digest>"
    }
  },
  "phase_spend_envelopes": {
    "image": "生产数据/spend_envelopes/image.json",
    "video": {
      "kind": "n2d_phase_spend_envelope",
      "version": 2,
      "envelope_id": "n2d-video-...",
      "line": "n2d",
      "project_id": "sha256:<resolved-project-id>",
      "stage": "video",
      "scope": {"episode": "第2集", "physical_clips": ["Clip_01"]},
      "model": "<concrete-model-version>",
      "channel": "<concrete-access-channel>",
      "input_sha256": "sha256:<canonical-producer-input>",
      "issued_at": "2026-08-20T10:00:00+08:00",
      "expires_at": "2026-08-20T18:00:00+08:00",
      "decision": "approved",
      "attempt_id_semantics": "phase_retry_round",
      "approver": "producer@example.com",
      "approval_reference": "approval-ticket-123",
      "source_quote": "批准本范围在费用上限内连续执行",
      "limits": {
        "max_calls": 8,
        "max_attempts": 2,
        "cost_ceiling": {"amount": 40, "currency": "work_units"}
      },
      "authorization_digest": "sha256:<canonical-authorization-digest>"
    }
  }
}
```

`production_authorizations` 是 v1 任务级兼容收据，不支持 task 通配。示例里的 `<...>` 只是 schema 占位，不能直接执行；受信任的审批面应调用 `runner.make_production_authorization(task, root=..., resolved_command=..., config=..., ...)`（或完全相同的 canonical JSON 算法）生成真实摘要。`task_digest` 绑定 task id、idempotency key、集/阶段、scope、估算成本与 `execution`；`authorization_digest` 是去掉自身字段后，对完整收据做 `sort_keys + compact separators + UTF-8` 的 SHA-256。任一字段被改写都会摘要不匹配。

v1 `execution` 四个摘要均必填：最终 resolved command；producer 的 canonical input；物理 submit/compiled request；完整 producer contract。image/video 由实际 producer API 重算，不能用 task 自报字段或 episode/prework fingerprint 代替。`attempt` 是一次性消费边界，retry 必须重新审批。voice/paid compose 在各自 producer 尚未提供 prepared canonical manifest 前 fail-closed。收据还必须有真实 `approver`、带时区且未过期的 `issued_at/expires_at`、显式 `model/channel`（无法预知时可以声明 `any`，但不能缺省）、以及 `ceiling.amount/currency`。估算成本必须与 currency 同单位且不超过 ceiling。重新规划、改变 scope/model/channel/成本、命令、producer 输入/请求或产生新 task/idempotency 后必须重新授权。也可由受信任上游把同结构收据写入 task 的 `production_authorization`。仅有 `queued`、runner 命令、配置项存在或旧任务授权均不放行。

`phase_spend_envelopes` 是 v2 阶段授权，可按 `task_id`、`stage_key` 或 `*` 查找，也可直接嵌入 task 的 `phase_spend_envelope`。路径相对作品根解析。必须由受信任的人审面用 `_lib/spend_envelope.py issue` 生成，runner/supervisor 不能 issue 或扩大；`approver + approval_reference + source_quote` 缺一不可，且拒绝 `agent:/delegate:/auto:/system:` 冒充真人。`scope/model/channel/input_sha256/expiry/max_calls/max_attempts/cost ceiling` 任一不匹配都 fail-closed。

v2 的 `attempt_id_semantics` 固定为 `phase_retry_round`：同一阶段重试轮里的多个 calls 共享 attempt ID，`max_attempts` 只统计唯一轮次；每个物理消费仍有唯一 `consumption_id`。当前 batch runner 用 `task_id:attempt`，因此同一个 task/round 只允许一次 consumption，任务内多调用须把总数写进 `calls`，不同物理任务使用不同 task ID。消费账本固定在 `生产数据/spend_envelope_usage.json`，首次 consume 原子写 `state=in_flight`；同 ID 重入或任一未完成 reservation 都阻断 provider 重提。只有绑定原 submit/query 的持久 completion evidence 才能 `finalize` 为 completed，不能换 attempt 绕过崩溃窗口。

`done` 同样不是普通状态赋值。queue 从 canonical stage contract 推导 hard completion；hard stage 的 `queue.py mark --status pass` 只接受 runner 自身 `status=pass / exit_code=0 / execution_started=true`（review 纯重验可为 false）、`completion.output_verification.status=pass`，以及声明了 gate 时的 `completion.post_gate.status=pass`。production 还必须让 authorization、execution binding 和每个 paid-boundary receipt 的摘要完全一致；无 gate 阶段必须显式为 `not_applicable`。提交锁内会按当前项目根重新检查每个 output binding 的路径、SHA 和媒体/图片解码，只有与 runner 验证值完全一致才写 `completion_commit={kind:n2d_batch_completion_commit, version:1, status:done, content_fingerprint, execution_binding, authorization_digest, completion, output_commit_attestation, acceptance, budget_settlement, digest}`；产物在验证后被删、替换或损坏会停在 `qa_blocked + completion_block_reason=output_changed_before_commit`。`digest` 是去掉自身后对完整 commit 做 canonical JSON SHA-256，`completion_commit_issue()` 可检查篡改和 task/attempt 串线。review 还必须通过 `_lib/acceptance_contract.py check_acceptance`，并把 receipt id + evidence digest 写入 commit：普通 gate、waiver、旧 signoff、缺失 `_进度.md` 行或 `验收` 列均不能替代 canonical acceptance receipt。若 receipt 尚未签，runner 保存 completion evidence、清除 worker/lease，并停在 `qa_blocked + completion_block_reason=needs_acceptance_signoff`；签收后 `mark pass` 原子复用 evidence 提交 done，无需重跑 review。外部 job receipt 的 `succeeded` 也只会停在 `qa_blocked`，不会直接提交完成。

runtime budget 与 planning budget 是两层不同口径。queue 的 production claim reservation 管本地 runtime cap；v2 spend ledger 另管真实人审 phase envelope 的调用/轮次/费用边界和 provider 重放风险。二者都必须通过，任何一层未知或超限都不提交。命令成功、产物/gate 阻断都按实际付费边界结算；只有 runner 明确证明 `execution_started=false` 且属于 preflight/config failure 才释放 queue reservation。这样并发 worker 既不能穿透 queue cap，也不能重复消费同一付费授权。

Command lookup order:

1. `runner.py --command` override;
2. task field `runner_command`;
3. `commands[stage_key]`;
4. `commands[owner]`;
5. `commands["*"]`;
6. task `command`.

If the resolved command starts with `/`, runner treats it as an agent slash command and marks the task failed/retryable. Configure a real shell command instead.

The repository-provided wrappers live under `skills/n2d/n2d-batch/scripts/`:

- `run_n2d_image.sh`: runs image_preflight gate, then executes explicit `N2D_IMAGE_COMMAND`.
- `run_n2d_video.sh`: runs identity/router/video_preflight gate, prepares video jobs, and only submits when `N2D_VIDEO_SUBMIT_ONE` or `N2D_VIDEO_AUTO_SUBMIT=1` is set. `video_runner.py submit` also runs video_preflight by default.
- `run_n2d_compose.sh`: runs compose gate, then calls `n2d-compose/compose.sh`.
- `run_n2d_review.sh`: refreshes spectacle video evidence, motion references, review gate, score, consistency ledger, and review-ui. It never writes `验收=✅`; human signoff remains explicit.

Do not hard-code this preflight inside `runner.py`; stage rules belong to the wrapper/stage skill, and runner only executes configured commands.

Template variables:

| Variable | Meaning |
|---|---|
| `{root}` | 作品根 |
| `{episode}` / `{ep}` | 集名 |
| `{task_id}` | task id |
| `{stage_key}` / `{stage}` | stage key |
| `{owner}` | owning n2d skill |
| `{reason}` | `progress` / `rerun` |
| `{scope}` | rerun scope |
| `{affected_shots}` | comma-separated affected shots |
| `{affected_artifacts}` | comma-separated affected artifacts |

Runner also injects environment variables:

```text
N2D_ROOT
N2D_EPISODE
N2D_TASK_ID
N2D_STAGE
N2D_OWNER
N2D_REASON
N2D_RERUN_SCOPE
N2D_AFFECTED_SHOTS
N2D_AFFECTED_ARTIFACTS
N2D_IDEMPOTENCY_KEY
```

## Runner telemetry

`runner.py` writes one `n2d-dashboard` manual event per executed task:

```json
{
  "source": "n2d-batch/scripts/runner.py",
  "event": "manual",
  "stage": "image",
  "duration_sec": 12.34,
  "meta": {
    "task_id": "001-image-progress",
    "runner_status": "pass",
    "exit_code": 0,
    "command": "bash scripts/run_n2d_image.sh \"创作区/制漫剧/剧名\" \"第1集\"",
    "attempt": 1,
    "idempotency_key": "n2d:...",
    "trace_id": "n2d:...",
    "error_class": ""
  }
}
```

This telemetry records worker execution time and exit code only. Real generation cost, redraw reason, and QA findings still belong to the corresponding stage skill and `n2d-dashboard record/gate`.

## Governance outputs

`governance.py` writes:

| File | Meaning |
|---|---|
| `production_slo.json` | Queue/stage SLO, created by `governance.py init-slo` |
| `batch_governance.json/md` | retry rate, dead-letter count, duration/attempt violations |
| `dead_letter_queue.json/md` | failed/dead-letter tasks with `error_class`, `note`, and `idempotency_key` |

Commands:

```bash
python3 skills/n2d/n2d-batch/scripts/governance.py init-slo <作品根>
python3 skills/n2d/n2d-batch/scripts/governance.py check <作品根> --write
python3 skills/n2d/n2d-batch/scripts/governance.py dead-letter <作品根> --write
```
