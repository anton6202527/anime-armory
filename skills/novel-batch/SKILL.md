---
name: novel-batch
description: Local batch queue and worker coordination for novel projects. Use when multiple chapters or project-level checks need to be reviewed, scored, refreshed, or dashboarded in parallel without double-claiming work. Provides a file-backed flock queue with leases, retries, reclaim, dead-letter reporting, and idempotent task planning. Does not write prose or call models by itself. Triggers novel-batch, 小说批量, 多章节并发, 批量审稿, 批量评分, 队列, worker, dead-letter, reclaim.
---

# novel-batch — 小说本地批量队列

`novel-batch` 是 novel 线的纯本地 worker 协调层。它只负责把“多章节/多任务”排成可认领、可恢复、可审计的队列，不直接写正文、不调用模型、不绕过任何 gate。

产物落在作品根：

- `生产数据/novel_batch_queue.json`
- `生产数据/novel_batch_queue.json.lock`
- `生产数据/batch_runs/<task_id>_attemptNN.json`
- `生产数据/batch_runs/<task_id>_attemptNN.stdout.log`
- `生产数据/batch_runs/<task_id>_attemptNN.stderr.log`

## 适用场景

- 多章节并行跑 `novel-review` 的读者契约/机检任务。
- 多章节或多 take 并行跑 `novel-score`。
- 批量刷新 `novel-dashboard`、统一修订计划、市场证据任务。
- 多个 worker 协作时防止重复处理同一章。

## 队列能力

- `flock` 原子认领：同一台机器多个 worker 不会双认领。
- 租约：worker 崩溃后，过期任务可 `reclaim` 回到 `retry_queued`。
- 重试：`max_retries` 用尽后进入 `dead_letter`。
- 幂等计划：同一 `kind + chapter + command` 反复 plan 会更新任务，不重复堆积。
- 可移植 JSON：不依赖 git、数据库或云服务。

## 工作流

### 1. 生成队列

```bash
python3 skills/novel-batch/scripts/queue.py plan "<作品根>" \
  --kind review \
  --chapters 1-10 \
  --max-retries 1 \
  --priority P1
```

常用 `kind`：

| kind | 默认命令 |
|---|---|
| `review` | 逐章 `reader_contract_sentry.py` |
| `score` | 逐章 `score.py --scope chapter` |
| `revision` | 项目级 `revision_planner.py` |
| `dashboard` | 项目级 `novel-dashboard --write` |
| `manual` | 自定义命令占位 |

需要自定义执行命令时：

```bash
python3 skills/novel-batch/scripts/queue.py plan "<作品根>" \
  --kind manual \
  --chapters 4-8 \
  --command-template 'python3 my_tool.py "{root}" --chapter {chapter}'
```

模板变量：`{root}`、`{chapter}`、`{chapter_label}`、`{task_id}`。

### 2. worker 认领

```bash
python3 skills/novel-batch/scripts/queue.py claim "<作品根>" --worker worker-a --json
```

返回任务 JSON 后，由 worker 执行其中的 `command`。本脚本不会自动执行命令，避免把队列层和模型/外部工具调用绑死。

需要本地自动执行时，使用显式 runner；默认只允许 allowlist 内的 novel 脚本，不走 shell，也不执行 `manual` 任意命令：

```bash
python3 skills/novel-batch/scripts/queue.py run-one "<作品根>" --worker worker-a --kind review
python3 skills/novel-batch/scripts/queue.py run-one "<作品根>" --worker worker-a --dry-run --json
```

`run-one` 每次都会写运行产物：命令 argv、返回码、耗时/子进程资源指标、stdout/stderr 日志、输出文件 diff，并把 `last_run_artifact` 回挂到队列任务；`novel-dashboard` 会汇总这些 batch run 指标。默认日志会脱敏并按单流 `NOVEL_BATCH_MAX_LOG_BYTES`（默认 256KiB）截断；确需保留完整脱敏日志时加 `--full-log`。输出 diff 默认只扫描小说生产目录，可用 `--snapshot-include/--snapshot-exclude` 明确收窄或扩展审计范围。

只有人工确认过的本机维护任务才可加 `--allow-manual`，否则 manual/echo/bash 等命令会失败并进入重试/死信流程。

### 3. 标记结果

```bash
python3 skills/novel-batch/scripts/queue.py mark "<作品根>" \
  --task-id "<task_id>" --worker worker-a --status pass
```

失败：

```bash
python3 skills/novel-batch/scripts/queue.py mark "<作品根>" \
  --task-id "<task_id>" --worker worker-a --status fail \
  --error-class ReviewFailed --message "reader_contract_sentry returned non-zero"
```

### 4. 崩溃恢复与死信

```bash
python3 skills/novel-batch/scripts/queue.py renew "<作品根>" --task-id "<task_id>" --worker worker-a
python3 skills/novel-batch/scripts/queue.py reclaim "<作品根>"
python3 skills/novel-batch/scripts/queue.py dead-letter "<作品根>" --json
python3 skills/novel-batch/scripts/queue.py status "<作品根>"
python3 skills/novel-batch/scripts/queue.py report "<作品根>"
```

`report` 会写 `生产数据/novel_batch_report.json/md`，汇总 dead-letter、retry_queued、过期 running lease 和建议处理动作。

## 与其它 skill 的边界

- `novel-craft/draft_queue.py` 管“正文写作章节认领”，粒度是写章。
- `novel-batch` 管“审稿/评分/看板/刷新等批量任务”，粒度是任意命令任务。
- `novel-supervisor` 可以读取队列状态并建议下一步，但不能绕过队列直接把同一任务分给多个 worker。
- `novel-dashboard` 只读汇总队列状态，不修改队列。

## 常见错误

| 错误 | 纠正 |
|---|---|
| 手工复制命令给多个 worker | 先 `plan`，再由 worker `claim` |
| worker 崩溃后直接重跑全部 | 先 `reclaim`，只处理回到 `retry_queued` 的任务 |
| 失败任务无限重试 | 设置 `--max-retries`，超过后查 `dead-letter` |
| 把队列当模型调用器 | 队列只分配任务；实际执行由 worker 或 supervisor 决定 |
