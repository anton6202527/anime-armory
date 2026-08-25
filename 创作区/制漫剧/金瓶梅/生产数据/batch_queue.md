# n2d 批量任务队列

- 更新时间：2026-08-24T07:57:54+00:00
- 最大并发：1
- 重试上限：1
- 预算：3.0 / None mixed
- 任务数：2
- 协调后端：local_file / lock=flock / status=ok

## 状态

| 状态 | 数量 |
|---|---:|
| blocked_agent | 1 |
| failed | 1 |

## 任务

| ID | 集 | Stage | Owner | 状态 | 尝试 | 估算成本 | 范围 |
|---|---|---|---|---|---:|---:|---|
| 001-script_stage1-rerun | 第1集 | script_stage1 | n2d-script | blocked_agent | 0 | 0.2 work_units | skill 更新后重制到 image |
| 001-image-rerun | 第1集 | image | n2d-image | failed | 5 | 3.0 work_units | 继续第1集出图：生成并验收 EP01_CLIP04_a1.png |
