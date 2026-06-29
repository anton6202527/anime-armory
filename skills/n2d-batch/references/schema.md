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
    "blocked_tasks": 0
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
  "last_error_class": "",
  "dead_letter": false,
  "dead_letter_at": "",
  "history": []
}
```

- `finding_fingerprints`：`(集×阶段×维度×最小定位)` 精确指纹（定位串过 `canonical_scope_key` 归一，同镜头不同写法/帧位/产物路径同指纹）；复检判 resolved/reopen + 防复审堆叠。
- `coarse_fingerprints`：`(集×阶段×维度)` 粗指纹；`recheck --coarse` 回退匹配用——精确指纹对不上但该桶仍有问题时不误判 resolved。
- `idempotency_key`：按作品根、集、stage、reason、rerun scope、affected shots/artifacts 生成的稳定键；runner 注入 `N2D_IDEMPOTENCY_KEY` 并写入 dashboard trace。
- `last_error_class`：失败分类，取值建议为 `preflight_block / capability / budget / timeout / output_contract / configuration / command_failed / unknown`。
- `dead_letter` / `dead_letter_at`：超过 `max_retries` 或最终 failed 后写入；由 `governance.py dead-letter` 汇总给人工处理。

## Status values

| Status | Meaning |
|---|---|
| `queued` | Ready to claim |
| `running` | Claimed by a worker/agent |
| `retry_queued` | Failed but still within retry limit |
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
    "voice": "python3 skills/n2d-voice/render_voice.py \"{root}\" \"{episode}\" zh",
    "image": "bash skills/n2d-batch/scripts/run_n2d_image.sh \"{root}\" \"{episode}\"",
    "video": "N2D_VIDEO_RANGE=06-10 bash skills/n2d-batch/scripts/run_n2d_video.sh \"{root}\" \"{episode}\"",
    "compose": "bash skills/n2d-batch/scripts/run_n2d_compose.sh \"{root}\" \"{episode}\" zh",
    "review": "bash skills/n2d-batch/scripts/run_n2d_review.sh \"{root}\" \"{episode}\"",
    "*": "bash scripts/run_stage.sh \"{stage_key}\" \"{root}\" \"{episode}\""
  },
  "env": {
    "NO_PROXY": "127.0.0.1,localhost",
    "N2D_IMAGE_COMMAND": "python3 my_image_runner.py \"$N2D_ROOT\" \"$N2D_EPISODE\""
  }
}
```

Command lookup order:

1. `runner.py --command` override;
2. task field `runner_command`;
3. `commands[stage_key]`;
4. `commands[owner]`;
5. `commands["*"]`;
6. task `command`.

If the resolved command starts with `/`, runner treats it as an agent slash command and marks the task failed/retryable. Configure a real shell command instead.

The repository-provided wrappers live under `skills/n2d-batch/scripts/`:

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
python3 skills/n2d-batch/scripts/governance.py init-slo <作品根>
python3 skills/n2d-batch/scripts/governance.py check <作品根> --write
python3 skills/n2d-batch/scripts/governance.py dead-letter <作品根> --write
```
