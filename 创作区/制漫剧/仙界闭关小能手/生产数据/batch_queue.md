# n2d 批量任务队列

- 更新时间：2026-06-29T13:11:23+00:00
- 最大并发：1
- 重试上限：1
- 预算：0.2 / None mixed
- 任务数：1
- 协调后端：local_file / lock=flock / status=ok

## 状态

| 状态 | 数量 |
|---|---:|
| queued | 1 |

## 任务

| ID | 集 | Stage | Owner | 状态 | 尝试 | 估算成本 | 范围 |
|---|---|---|---|---|---:|---:|---|
| 001-script_stage1-rerun | 第1集 | script_stage1 | n2d-script | queued | 0 | 0.2 work_units | skill 更新后重制到 image·复用共享定妆库·只重出本集分镜帧 |
