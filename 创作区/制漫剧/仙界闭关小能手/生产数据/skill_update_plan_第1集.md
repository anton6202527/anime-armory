# skill 更新重制计划 — 第1集

- 作品根：`/Users/lalala/learn/anime-armory/创作区/制漫剧/仙界闭关小能手`
- 当前阶段：`review`
- 建议动作：`重制` · `script_stage1` → `review`
- 需要重制：是
- 重制策略：`最小`
- 共享定妆库：需复核（变更命中定妆库生产规则：skills/n2d-image/SKILL.md）
- 需刷新 gate/QC：是（image）
- 变动 skill：n2d, n2d-batch, n2d-image, n2d-review, n2d-script, n2d-video
- 新纳入范围（不计变更）：n2d-compose

## 变动文件
- `skills/n2d-batch/SKILL.md`
- `skills/n2d-batch/scripts/governance.py`
- `skills/n2d-image/SKILL.md`
- `skills/n2d-image/scripts/codex_image_runner.py`
- `skills/n2d-image/scripts/dreamina_image_runner.py`
- `skills/n2d-image/scripts/image_prompt_pack.py`
- `skills/n2d-image/scripts/image_qc.py`
- `skills/n2d-image/scripts/keyshot_candidate_runner.py`
- `skills/n2d-review/SKILL.md`
- `skills/n2d-review/scripts/face_consistency.py`
- `skills/n2d-review/scripts/gate.py`
- `skills/n2d-review/scripts/gate_core.py`
- `skills/n2d-review/scripts/gates/backend.py`
- `skills/n2d-review/scripts/gates/consistency.py`
- `skills/n2d-review/scripts/gates/contract.py`
- `skills/n2d-review/scripts/gates/evidence.py`
- `skills/n2d-review/scripts/gates/face.py`
- `skills/n2d-review/scripts/hand_anatomy.py`
- `skills/n2d-review/scripts/mechanical_check.py`
- `skills/n2d-review/scripts/script_contract_verify.py`
- `skills/n2d-review/scripts/spectacle_motion_measure.py`
- `skills/n2d-script/SKILL.md`
- `skills/n2d-script/finalize_storyboard.py`
- `skills/n2d-script/scripts/anchor_planner.py`
- `skills/n2d-script/scripts/beat_audit.py`
- `skills/n2d-script/scripts/production_breakdown.py`
- `skills/n2d-script/scripts/source_adaptation_audit.py`
- `skills/n2d-script/scripts/source_language.py`
- `skills/n2d-script/validate_storyboard_contract.py`
- `skills/n2d-video/SKILL.md`
- `skills/n2d-video/references/platforms.md`
- `skills/n2d-video/references/prompt_format.md`
- `skills/n2d-video/references/原生音画opt-in.md`
- `skills/n2d-video/scripts/lipsync_pass.py`
- `skills/n2d-video/scripts/native_av_sidecar.py`
- `skills/n2d-video/scripts/video_runner.py`
- `skills/n2d/SKILL.md`
- `skills/n2d/_lib/n2d_action_registry.py`
- `skills/n2d/_lib/n2d_platform_profiles.py`
- `skills/n2d/_lib/n2d_spectacle.py`
- `skills/n2d/_lib/settings.py`
- `skills/n2d/_lib/video_backend_adapter.py`
- `skills/n2d/progress.py`
- `skills/n2d/references/选择点与偏好.md`
- `skills/n2d/run.py`
- `skills/n2d/scripts/audience_experience.py`
- `skills/n2d/scripts/contract_trace.py`
- `skills/n2d/scripts/failure_taxonomy.py`
- `skills/n2d/scripts/pilot_check.py`
- `skills/n2d/scripts/pilot_risk_sampler.py`
- `skills/n2d/scripts/preventive_contracts.py`
- `skills/n2d/scripts/release_verdict.py`
- `skills/n2d/scripts/stop_loss.py`

## 当前生产缺口
- 当前待办：`审查验收`（验收 = `⬜`）
- 建议 skill：`n2d-review`
- 建议命令：`n2d-review /Users/lalala/learn/anime-armory/创作区/制漫剧/仙界闭关小能手 第1集`

## 图片质检环境与阶段跳转
- 机检能力：`full`
- 当前解释器：`/opt/homebrew/Caskroom/miniforge/base/envs/facefusion/bin/python`
- 当前 image_qc：`verdict=review`，硬阻断 `0`，非阻断初筛 `103`，降级 `False`
- block 摘要：脸(G1): 图片/Clip13_end.png | 脸(G1): 图片/Clip14_end.png
- 当前应停在/回退：`video` — full image_qc 仅有非阻断初筛项，已作为 gate warn 入账；不阻断进入 video
- 建议安装：无需补装
- 报告：`/Users/lalala/learn/anime-armory/创作区/制漫剧/仙界闭关小能手/生产数据/image_qc/第1集/image_qc_第1集.md`

## 健康检测（源/三帧/图片/契约继承）
- **源小说**：✅ 源未变动
- **三帧契约**：豁免（后端 `None` 不支持≥3帧·能力门控）
- **图片一致性**：✅ 无硬阻断（verdict=`review`，精度 `full`）
- **契约继承**：✅ 已继承（verdict=`pass`）

## 执行步骤
1. `queue_bounded_rerun`
```bash
python3 skills/n2d-batch/scripts/queue.py plan "/Users/lalala/learn/anime-armory/创作区/制漫剧/仙界闭关小能手" --episodes 1 --rerun-from script_stage1 --scope "skill 更新后重制到 review" --max-concurrency 1 --max-retries 1
```
2. `manual_alternative`：排队后由 n2d-batch runner 或对应 stage skill 执行返工；不要同时手工运行阶段命令，避免队列账本与实际产物分叉。 手工替代路径仅在不使用 batch 时执行：`n2d-script /Users/lalala/learn/anime-armory/创作区/制漫剧/仙界闭关小能手 第1集`
3. `verify_after_image_regen`
   - 运行条件：仅在 n2d-batch/阶段 skill 已实际完成图片重出后运行；只生成队列计划时不要当作已验收。
```bash
python3 skills/n2d-dashboard/scripts/dashboard.py gate "/Users/lalala/learn/anime-armory/创作区/制漫剧/仙界闭关小能手" 第1集 --stage image  # 重出图后验像素一致性（含 image_qc）
```

## 备注
- n2d-compose 因阶段推进首次纳入相关范围，本次不计为变更；该阶段完成后请 record 刷新基线。
- 真正执行前先看 diff/计划；涉及出图/出视频/配音/合成等付费或不可逆步骤时必须再次确认。
- 共享定妆库需复核（非默认沿用）：本次变更命中定妆库生产规则（skills/n2d-image/SKILL.md）。先按最新规则复核、必要时重出共享定妆/场景，再用 `python3 skills/n2d-image/scripts/asset_impact.py <作品根> <改动的定妆资产>` 级联出引用它、需跟着重出的本集分镜。
- 三帧契约豁免：路由后端 None 不支持≥3帧（能力门控自动豁免），本集不强制中段锚帧。
- 图片一致性报告已过期（image_qc 之后出图被重生成，inputs_fingerprint 失配）：当前结论不可信，先重跑 `python3 skills/n2d-image/scripts/image_qc.py <作品根> 第1集` 再据此判断。
- 契约继承报告已过期（生成后出图/出视频 prompt 又改了，inputs_fingerprint 失配）：`inherited` 结论不可信，先重跑 `python3 skills/n2d-video/scripts/inherit_contract.py <作品根> 第1集` 再判。
