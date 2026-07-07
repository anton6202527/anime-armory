# skill 更新重制计划 — 第1集

- 作品根：`/Users/wesley/learn/anime-armory/创作区/制漫剧/那妖魔是姜大人`
- 当前阶段：`review`
- 建议动作：`重制` · `script_stage1` → `review`
- 需要重制：是
- 重制策略：`最小`
- 共享定妆库：需复核（变更命中定妆库生产规则：skills/n2d-image/SKILL.md, skills/n2d-image/references/角色一致性checklist.md）
- 变动 skill：n2d, n2d-compose, n2d-dashboard, n2d-image, n2d-review, n2d-script, n2d-video

## 变动文件
- `skills/n2d-compose/compose.sh`
- `skills/n2d-compose/scripts/final_timeline_probe.py`
- `skills/n2d-compose/scripts/foley_agent.py`
- `skills/n2d-compose/tension_mix.py`
- `skills/n2d-dashboard/scripts/dashboard.py`
- `skills/n2d-image/SKILL.md`
- `skills/n2d-image/references/角色一致性checklist.md`
- `skills/n2d-image/scripts/codex_image_runner.py`
- `skills/n2d-image/scripts/image_prompt_pack.py`
- `skills/n2d-review/SKILL.md`
- `skills/n2d-review/references/checklist.md`
- `skills/n2d-review/scripts/demo_preview_packet.py`
- `skills/n2d-review/scripts/gate.py`
- `skills/n2d-review/scripts/gate_core.py`
- `skills/n2d-review/scripts/gates/asset.py`
- `skills/n2d-review/scripts/gates/contract.py`
- `skills/n2d-review/scripts/gates/face.py`
- `skills/n2d-review/scripts/mechanical_check.py`
- `skills/n2d-review/scripts/production_consistency.py`
- `skills/n2d-review/scripts/temporal_consistency.py`
- `skills/n2d-review/scripts/video_face_drift_watch.py`
- `skills/n2d-script/SKILL.md`
- `skills/n2d-script/finalize_storyboard.py`
- `skills/n2d-script/references/分镜语法.md`
- `skills/n2d-script/scripts/anchor_planner.py`
- `skills/n2d-script/scripts/beat_audit.py`
- `skills/n2d-script/scripts/director_camera_plan.py`
- `skills/n2d-script/scripts/story_integrity_audit.py`
- `skills/n2d-script/validate_storyboard_contract.py`
- `skills/n2d-video/SKILL.md`
- `skills/n2d-video/scripts/prompt_pack.py`
- `skills/n2d-video/scripts/script_contract_receipt.py`
- `skills/n2d/SKILL.md`
- `skills/n2d/_lib/n2d_spectacle.py`
- `skills/n2d/_lib/settings.py`
- `skills/n2d/references/选择点与偏好.md`
- `skills/n2d/scripts/contract_trace.py`
- `skills/n2d/scripts/generation_recipe_manifest.py`
- `skills/n2d/scripts/pilot_check.py`

## 当前生产缺口
- 当前待办：`审查验收`（验收 = `⬜`）
- 建议 skill：`n2d-review`
- 建议命令：`n2d-review /Users/wesley/learn/anime-armory/创作区/制漫剧/那妖魔是姜大人 第1集`

## 图片质检环境与阶段跳转
- 机检能力：`full`
- 当前解释器：`/opt/homebrew/Caskroom/miniforge/base/envs/facefusion/bin/python`
- 当前 image_qc：`verdict=review`，硬阻断 `0`，非阻断初筛 `72`，降级 `False`
- block 摘要：证据等级未达标(PENDING)：主体视频一致(S2V) 本可验到 embedding/pixel 级，本次只到结构/启发式级（torch-DINOv2 跨帧主体一致 / SyncNet 口型词级 进阶依赖未装，未数值化验证）；本集最弱证据级=structured。交付边界不放行——在装好进阶依赖的环境复跑，或显式 N2D_ALLOW_DEGRADED_QC=1 自负其责。 | 场景语义嵌入(DINOv2) 适用却休眠：项目登记了它要查的数据，但交付前它没真跑（缺后端/sidecar）——「跑了数据却没执行一致性」正是这种休眠。装好后端真验，或显式 N2D_ALLOW_DEGRADED_QC=1 计债放行。跑 python3 skills/n2d-review/scripts/scene_embed.py "创作区/制漫剧/那妖魔是姜大人" 第1集 --write（需对应重型后端 env）
- 当前应停在/回退：`video` — full image_qc 仅有非阻断初筛项，已作为 gate warn 入账；不阻断进入 video
- 建议安装：无需补装
- 报告：`/Users/wesley/learn/anime-armory/创作区/制漫剧/那妖魔是姜大人/生产数据/image_qc/第1集/image_qc_第1集.md`

## 健康检测（源/三帧/图片/契约继承）
- **源小说**：✅ 源未变动
- **三帧契约**：豁免（后端 `deferred_auto_route` 不支持≥3帧·能力门控）
- **图片一致性**：✅ 无硬阻断（verdict=`review`，精度 `full`）
- **契约继承**：✅ 已继承（verdict=`pass`）

## 执行步骤
1. `queue_bounded_rerun`
```bash
python3 skills/n2d-batch/scripts/queue.py plan "/Users/wesley/learn/anime-armory/创作区/制漫剧/那妖魔是姜大人" --episodes 1 --rerun-from script_stage1 --scope "skill 更新后重制到 review" --max-concurrency 1 --max-retries 1
```
2. `manual_alternative`：排队后由 n2d-batch runner 或对应 stage skill 执行返工；不要同时手工运行阶段命令，避免队列账本与实际产物分叉。 手工替代路径仅在不使用 batch 时执行：`n2d-script /Users/wesley/learn/anime-armory/创作区/制漫剧/那妖魔是姜大人 第1集`
3. `verify_after_image_regen`
   - 运行条件：仅在 n2d-batch/阶段 skill 已实际完成图片重出后运行；只生成队列计划时不要当作已验收。
```bash
python3 skills/n2d-dashboard/scripts/dashboard.py gate "/Users/wesley/learn/anime-armory/创作区/制漫剧/那妖魔是姜大人" 第1集 --stage image  # 重出图后验像素一致性（含 image_qc）
```

## 备注
- 真正执行前先看 diff/计划；涉及出图/出视频/配音/合成等付费或不可逆步骤时必须再次确认。
- 共享定妆库需复核（非默认沿用）：本次变更命中定妆库生产规则（skills/n2d-image/SKILL.md, skills/n2d-image/references/角色一致性checklist.md）。先按最新规则复核、必要时重出共享定妆/场景，再用 `python3 skills/n2d-image/scripts/asset_impact.py <作品根> <改动的定妆资产>` 级联出引用它、需跟着重出的本集分镜。
- 三帧契约豁免：路由后端 deferred_auto_route 不支持≥3帧（能力门控自动豁免），本集不强制中段锚帧。
