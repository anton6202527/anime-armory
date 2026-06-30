# n2d 批量任务队列

- 更新时间：2026-06-30T07:54:14+00:00
- 最大并发：1
- 重试上限：1
- 预算：0.7 / None mixed
- 任务数：3
- 协调后端：local_file / lock=flock / status=ok

## 状态

| 状态 | 数量 |
|---|---:|
| done | 3 |

## 任务

| ID | 集 | Stage | Owner | 状态 | 尝试 | 估算成本 | 范围 |
|---|---|---|---|---|---:|---:|---|
| 001-script_stage1-rerun | 第1集 | script_stage1 | n2d-script | done | 1 | 0.2 work_units | skill 更新后重制到 image |
| 001-script_stage1-rerun-2 | 第1集 | script_stage1 | n2d-script | done | 2 | 0.2 work_units | skill 更新后重制到 video |
| 001-script_stage2-rerun | 第1集 | script_stage2 | n2d-script | done | 2 | 0.3 work_units | skill 更新后继续重制到 video（script_stage1 已完成） |
