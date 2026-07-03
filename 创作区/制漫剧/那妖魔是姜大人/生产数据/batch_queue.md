# n2d 批量任务队列

- 更新时间：2026-07-03T14:51:25+00:00
- 最大并发：1
- 重试上限：1
- 预算：1.2 / None mixed
- 任务数：3
- 协调后端：local_file / lock=flock / status=ok

## 状态

| 状态 | 数量 |
|---|---:|
| done | 3 |

## 任务

| ID | 集 | Stage | Owner | 状态 | 尝试 | 估算成本 | 范围 |
|---|---|---|---|---|---:|---:|---|
| 002-script_stage1-rerun | 第2集 | script_stage1 | n2d-script | done | 0 | 0.2 work_units | skill 更新后重制到 image |
| 001-script_stage1-rerun | 第1集 | script_stage1 | n2d-script | done | 0 | 0.2 work_units | skill 更新后重制到 video（不含 compose） |
| 001-voice-progress | 第1集 | voice | n2d-voice | done | 0 | 1.0 work_units | — |
