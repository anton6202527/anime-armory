# n2d 批量任务队列

- 更新时间：2026-09-01T04:06:15+00:00
- 最大并发：2
- 重试上限：1
- 预算：3.0 / 24.0 work_units
- 任务数：5
- 协调后端：local_file / lock=flock / status=ok

## 状态

| 状态 | 数量 |
|---|---:|
| blocked_agent | 2 |
| cancelled | 3 |

## 任务

| ID | 集 | Stage | Owner | 状态 | 尝试 | 估算成本 | 范围 |
|---|---|---|---|---|---:|---:|---|
| 001-script_stage1-rerun | 第1集 | script_stage1 | n2d-script | blocked_agent | 0 | 0.2 work_units | skill 更新后重制到 image |
| 001-image-rerun | 第1集 | image | n2d-image | cancelled | 5 | 3.0 work_units | 继续第1集出图：生成并验收 EP01_CLIP04_a1.png |
| 001-script_stage1-rerun-2 | 第1集 | script_stage1 | n2d-script | blocked_agent | 0 | 0.2 work_units | skill 更新后重制到 image |
| 001-image-rerun-2 | 第1集 | image | n2d-image | cancelled | 2 | 3.0 work_units | 2026-09-01 user-confirmed exact rerender of eight PNGs missing generation lineage |
| 001-image-rerun-3 | 第1集 | image | n2d-image | cancelled | 2 | 3.0 work_units | 2026-09-01 user-confirmed exact rerender of eight PNGs missing generation lineage |
