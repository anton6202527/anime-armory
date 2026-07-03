# n2d 批量任务队列

- 更新时间：2026-07-03T11:28:14+00:00
- 最大并发：1
- 重试上限：1
- 预算：20.2 / None mixed
- 任务数：14
- 协调后端：local_file / lock=flock / status=ok

## 状态

| 状态 | 数量 |
|---|---:|
| blocked_agent | 1 |
| cancelled | 1 |
| done | 11 |
| queued | 1 |

## 任务

| ID | 集 | Stage | Owner | 状态 | 尝试 | 估算成本 | 范围 |
|---|---|---|---|---|---:|---:|---|
| 001-script_stage1-rerun | 第1集 | script_stage1 | n2d-script | done | 1 | 0.2 work_units | skill 更新后重制到 image |
| 001-script_stage1-rerun-2 | 第1集 | script_stage1 | n2d-script | done | 2 | 0.2 work_units | skill 更新后重制到 video |
| 001-script_stage2-rerun | 第1集 | script_stage2 | n2d-script | done | 2 | 0.3 work_units | skill 更新后继续重制到 video（script_stage1 已完成） |
| 001-script_stage1-rerun-3 | 第1集 | script_stage1 | n2d-script | cancelled | 2 | 0.2 work_units | skill 更新后重制到 video |
| 001-script_stage1-rerun-4 | 第1集 | script_stage1 | n2d-script | done | 1 | 0.2 work_units | skill 更新后重制到 video（第1集边界签收限定重跑） |
| 001-script_stage2-rerun-2 | 第1集 | script_stage2 | n2d-script | done | 1 | 0.3 work_units | skill 更新后继续重制到 video（script_stage1 已完成·current root） |
| 001-video-rerun | 第1集 | video | n2d-video | queued | 0 | 12.0 work_units | VSEM DINOv2 端点漂移：Clip_02 尾帧未落到张老大压迫近景，Clip_04 首帧为空镜/屋顶光束；重出对应 MP4 后重跑 video_semantic_runner 与 video gate。 |
| 001-script_stage2-rerun-3 | 第1集 | script_stage2 | n2d-script | done | 1 | 0.3 work_units | Rhythm production blocker：节奏/留存 67.8，连续 11 个长镜聚集；回阶段2重切镜头时长曲线、补钩子/爽点/集尾 cliffhanger。会使后续图/视频需按确认范围重刷。 |
| 001-script_stage1-rerun-5 | 第1集 | script_stage1 | n2d-script | blocked_agent | 0 | 0.2 work_units | skill 更新后重制到 video·复用共享定妆库·只重出本集分镜帧 |
| 001-script_stage1-rerun-6 | 第1集 | script_stage1 | n2d-script | done | 0 | 0.2 work_units | skill 更新后重制到 image·复用共享定妆库·只重出本集分镜帧 |
| 001-script_stage2-rerun-4 | 第1集 | script_stage2 | n2d-script | done | 0 | 0.3 work_units | skill 更新后继续重制到 image·script_stage1 已验证·复用共享定妆库 |
| 001-image-rerun | 第1集 | image | n2d-image | done | 0 | 3.0 work_units | skill 更新后重制到 image·复用共享定妆库·优先修复 image_qc hard blocks |
| 002-image_prompt-rerun | 第2集 | image_prompt | n2d-image | done | 0 | 0.2 work_units | skill 更新后重制到 image |
| 002-image-rerun | 第2集 | image | n2d-image | done | 0 | 3.0 work_units | skill 更新后重制到 image；严格刷新 Clip_01-27 |
