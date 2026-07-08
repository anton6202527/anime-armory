# skill 更新重制计划 — 第4集

- 作品根：`/Users/lalala/learn/anime-armory/创作区/制漫剧/那妖魔是姜大人`
- 当前阶段：`video_prompt`
- 建议动作：`重制` · `script_stage1` → `video_prompt`
- 需要重制：是
- 重制策略：`最小`
- 共享定妆库：需复核（变更命中定妆库生产规则：skills/n2d-image/SKILL.md, skills/n2d-image/references/cli_registry.md, skills/n2d-image/references/lora_consistency.md, skills/n2d-image/references/platforms.md, skills/n2d-image/references/prompt_format.md）
- 需刷新 gate/QC：是（image）
- 变动 skill：n2d, n2d-batch, n2d-image, n2d-review, n2d-script, n2d-video

## 变动文件
- `skills/n2d-batch/SKILL.md`
- `skills/n2d-batch/scripts/queue.py`
- `skills/n2d-image/QUICKSTART.md`
- `skills/n2d-image/SKILL.md`
- `skills/n2d-image/references/cli_registry.md`
- `skills/n2d-image/references/lora_consistency.md`
- `skills/n2d-image/references/platforms.md`
- `skills/n2d-image/references/prompt_format.md`
- `skills/n2d-image/scripts/codex_image_runner.py`
- `skills/n2d-image/scripts/derive_makeup_pack.py`
- `skills/n2d-image/scripts/dreamina_image_runner.py`
- `skills/n2d-image/scripts/image_prompt_pack.py`
- `skills/n2d-image/scripts/image_qc.py`
- `skills/n2d-review/SKILL.md`
- `skills/n2d-review/references/checklist.md`
- `skills/n2d-review/scripts/consistency_audit.py`
- `skills/n2d-review/scripts/consistency_charter.py`
- `skills/n2d-review/scripts/gate.py`
- `skills/n2d-review/scripts/gate_core.py`
- `skills/n2d-review/scripts/gates/backend.py`
- `skills/n2d-review/scripts/gates/consistency.py`
- `skills/n2d-review/scripts/gates/contract.py`
- `skills/n2d-review/scripts/video_face_drift_watch.py`
- `skills/n2d-script/SKILL.md`
- `skills/n2d-script/references/formats.md`
- `skills/n2d-script/references/platforms.md`
- `skills/n2d-script/references/专项镜头模板库.md`
- `skills/n2d-script/scripts/animatic_assembler.py`
- `skills/n2d-script/scripts/director_blocking_pack.py`
- `skills/n2d-script/scripts/production_breakdown.py`
- `skills/n2d-script/scripts/shot_split_decision.py`
- `skills/n2d-script/scripts/story_acceptance_packets.py`
- `skills/n2d-script/scripts/story_economy_audit.py`
- `skills/n2d-script/scripts/storyboard_contract_backfill.py`
- `skills/n2d-video/SKILL.md`
- `skills/n2d-video/references/platforms.md`
- `skills/n2d-video/scripts/prompt_pack.py`
- `skills/n2d-video/scripts/video_runner.py`
- `skills/n2d/Q&A.md`
- `skills/n2d/SKILL.md`
- `skills/n2d/_lib/continuity_chain.py`
- `skills/n2d/_lib/gate_policy_matrix.json`
- `skills/n2d/_lib/image_backend_adapter.py`
- `skills/n2d/_lib/n2d_action_registry.py`
- `skills/n2d/_lib/prework_cache.py`
- `skills/n2d/_lib/settings.py`
- `skills/n2d/references/architecture.md`
- `skills/n2d/references/contract.md`
- `skills/n2d/references/制作模式与视频路由.md`
- `skills/n2d/references/模型矩阵.md`
- `skills/n2d/references/选择点与偏好.md`
- `skills/n2d/run.py`
- `skills/n2d/scripts/creative_governance.py`
- `skills/n2d/scripts/gate_policy_coverage.py`
- `skills/n2d/scripts/preventive_contracts.py`
- `skills/n2d/scripts/production_locks.py`
- `skills/n2d/scripts/production_readiness.py`
- `skills/n2d/scripts/release_verdict.py`
- `skills/n2d/scripts/repair_preflight.py`
- `skills/n2d/scripts/script_supervisor_log.py`

## 当前生产缺口
- 当前待办：`视频prompt`（视频prompt = `⬜`）
- 建议 skill：`n2d-video`
- 建议命令：`n2d-video /Users/lalala/learn/anime-armory/创作区/制漫剧/那妖魔是姜大人 第4集`

## 图片质检环境与阶段跳转
- 机检能力：`full`
- 当前解释器：`/opt/homebrew/Caskroom/miniforge/base/envs/facefusion/bin/python`
- 当前 image_qc：`verdict=review`，硬阻断 `0`，非阻断初筛 `36`，降级 `False`
- block 摘要：角色资产包分区不存在：reference | 角色资产包分区不存在：prompts
- 当前应停在/回退：`video` — full image_qc 仅有非阻断初筛项，已作为 gate warn 入账；不阻断进入 video
- 建议安装：无需补装
- 报告：`/Users/lalala/learn/anime-armory/创作区/制漫剧/那妖魔是姜大人/生产数据/image_qc/第4集/image_qc_第4集.md`

## 健康检测（源/三帧/图片/契约继承）
- **源小说**：✅ 源未变动
- **三帧契约**：豁免（后端 `None` 不支持≥3帧·能力门控）
- **图片一致性**：✅ 无硬阻断（verdict=`review`，精度 `full`）
- **契约继承**：— 未校验（缺 inherit_contract 报告，先跑 n2d-video `inherit_contract.py`）

## 执行步骤
1. `queue_bounded_rerun`
```bash
python3 skills/n2d-batch/scripts/queue.py plan "/Users/lalala/learn/anime-armory/创作区/制漫剧/那妖魔是姜大人" --episodes 4 --rerun-from script_stage1 --scope "skill 更新后重制到 video_prompt" --max-concurrency 1 --max-retries 1
```
2. `manual_alternative`：排队后由 n2d-batch runner 或对应 stage skill 执行返工；不要同时手工运行阶段命令，避免队列账本与实际产物分叉。 手工替代路径仅在不使用 batch 时执行：`n2d-script /Users/lalala/learn/anime-armory/创作区/制漫剧/那妖魔是姜大人 第4集`
3. `verify_after_image_regen`
   - 运行条件：仅在 n2d-batch/阶段 skill 已实际完成图片重出后运行；只生成队列计划时不要当作已验收。
```bash
python3 skills/n2d-dashboard/scripts/dashboard.py gate "/Users/lalala/learn/anime-armory/创作区/制漫剧/那妖魔是姜大人" 第4集 --stage image  # 重出图后验像素一致性（含 image_qc）
```

## 备注
- 真正执行前先看 diff/计划；涉及出图/出视频/配音/合成等付费或不可逆步骤时必须再次确认。
- 共享定妆库需复核（非默认沿用）：本次变更命中定妆库生产规则（skills/n2d-image/SKILL.md, skills/n2d-image/references/cli_registry.md, skills/n2d-image/references/lora_consistency.md, skills/n2d-image/references/platforms.md, skills/n2d-image/references/prompt_format.md）。先按最新规则复核、必要时重出共享定妆/场景，再用 `python3 skills/n2d-image/scripts/asset_impact.py <作品根> <改动的定妆资产>` 级联出引用它、需跟着重出的本集分镜。
- 三帧契约豁免：路由后端 None 不支持≥3帧（能力门控自动豁免），本集不强制中段锚帧。
- 图片一致性报告已过期（image_qc 之后出图被重生成，inputs_fingerprint 失配）：当前结论不可信，先重跑 `python3 skills/n2d-image/scripts/image_qc.py <作品根> 第4集` 再据此判断。
- 出图→出视频视觉契约继承尚未校验：缺 `/Users/lalala/learn/anime-armory/创作区/制漫剧/那妖魔是姜大人/生产数据/contract_inheritance_第4集.json`。先跑 `python3 skills/n2d-video/scripts/inherit_contract.py <作品根> 第4集`，校验参考帧契约（色调/光位锚/轴线视线/角色状态演进/景别）+ 文字 prompt 是否从出图侧正确传到出视频侧、命名角色镜是否锁脸、出图绑定的场景/道具/特效资产是否丢失，再出视频。
