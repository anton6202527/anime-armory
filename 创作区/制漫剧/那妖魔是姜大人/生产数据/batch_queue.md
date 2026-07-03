# n2d 批量任务队列

- 更新时间：2026-07-03T04:11:55+00:00
- 最大并发：1
- 重试上限：1
- 预算：0.0 / None mixed
- 任务数：1
- 协调后端：local_file / lock=flock / status=ok

## 状态

| 状态 | 数量 |
|---|---:|
| blocked_agent | 1 |

## 任务

| ID | 集 | Stage | Owner | 状态 | 尝试 | 估算成本 | 范围 |
|---|---|---|---|---|---:|---:|---|
| 002-script_stage1-rerun | 第2集 | script_stage1 | n2d-script | blocked_agent | 0 | 0.2 work_units | skill 更新后重制到 image |
