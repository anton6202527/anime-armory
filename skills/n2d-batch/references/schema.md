# n2d-batch schema

## Queue file

Path:

```text
制漫剧/<剧名>/生产数据/batch_queue.json
```

Shape:

```json
{
  "kind": "n2d_batch_queue",
  "version": 1,
  "root": "制漫剧/剧名",
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
  "command": "/n2d-image 制漫剧/剧名 第2集",
  "gate_stage": "image",
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
  "history": []
}
```

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
制漫剧/<剧名>/生产数据/batch_runner.json
```

Shape:

```json
{
  "commands": {
    "voice": "python3 skills/n2d-voice/render_voice.py \"{root}\" \"{episode}\" zh",
    "image": "bash scripts/run_n2d_image.sh \"{root}\" \"{episode}\"",
    "n2d-video": "bash scripts/run_n2d_video.sh \"{root}\" \"{episode}\"",
    "*": "bash scripts/run_stage.sh \"{stage_key}\" \"{root}\" \"{episode}\""
  },
  "env": {
    "NO_PROXY": "127.0.0.1,localhost"
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

For `video` / `n2d-video`, the configured shell wrapper must run model routing before any paid video call:

```bash
python3 skills/n2d-model-router/scripts/router.py "$root" "$episode" --write
# then generate/update video prompts and run n2d-review gate --stage video
```

Do not hard-code this preflight inside `runner.py`; stage rules belong to `n2d-video` / `n2d-model-router`, and runner only executes configured commands.

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
    "command": "bash scripts/run_n2d_image.sh \"制漫剧/剧名\" \"第1集\"",
    "attempt": 1
  }
}
```

This telemetry records worker execution time and exit code only. Real generation cost, redraw reason, and QA findings still belong to the corresponding stage skill and `n2d-dashboard record/gate`.
