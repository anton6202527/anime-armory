# n2d 批量任务队列

- 更新时间：2026-06-30T17:32:21+00:00
- 最大并发：1
- 重试上限：1
- 预算：3.0 / None mixed
- 任务数：1
- 协调后端：local_file / lock=flock / status=ok

## 状态

| 状态 | 数量 |
|---|---:|
| failed | 1 |

## 任务

| ID | 集 | Stage | Owner | 状态 | 尝试 | 估算成本 | 范围 |
|---|---|---|---|---|---:|---:|---|
| 001-image-rerun | 第1集 | image | n2d-image | failed | 2 | 3.0 work_units | image_preflight 已过；按最新中性灰角色定妆与 LOC/PROP/VFX 共享资产重出第1集全部 Clip 图 |
