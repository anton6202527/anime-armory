# skill 更新重制计划 — 第1集

- 作品根：`/Users/lalala/learn/anime-arsenal/创作区/制漫剧/金睛缉妖录`
- 当前阶段：`image`
- 建议动作：`重制` · `script_stage1` → `image`
- 需要重制：是
- 重制策略：`最小`
- 共享定妆库：需复核（变更命中定妆库生产规则：skills/n2d-image/SKILL.md, skills/n2d-image/references/prompt_format.md）
- 需刷新 gate/QC：是（image）
- 变动 skill：n2d, n2d-batch, n2d-image, n2d-review, n2d-script

## 变动文件
- `skills/n2d-batch/scripts/queue.py`
- `skills/n2d-batch/scripts/runner.py`
- `skills/n2d-image/SKILL.md`
- `skills/n2d-image/references/prompt_format.md`
- `skills/n2d-image/scripts/codex_image_runner.py`
- `skills/n2d-image/scripts/image_prompt_pack.py`
- `skills/n2d-image/scripts/image_qc.py`
- `skills/n2d-image/scripts/reference_planner.py`
- `skills/n2d-image/scripts/style_attribution.py`
- `skills/n2d-review/scripts/gate.py`
- `skills/n2d-review/scripts/gates/face.py`
- `skills/n2d-review/scripts/production_consistency.py`
- `skills/n2d-review/scripts/scene_consistency.py`
- `skills/n2d-review/scripts/temporal_consistency.py`
- `skills/n2d-review/scripts/video_semantic_runner.py`
- `skills/n2d-script/SKILL.md`
- `skills/n2d-script/references/formats.md`
- `skills/n2d-script/scripts/series_balance.py`
- `skills/n2d-script/scripts/spectacle_sequence_plan.py`
- `skills/n2d-script/validate_storyboard_contract.py`
- `skills/n2d/_lib/n2d_handoff.py`
- `skills/n2d/scripts/genre_packs.py`

## 当前生产缺口
- 当前待办：`出图返修`（出图 = `⬜`）
- 建议 skill：`n2d-image`
- 建议命令：`n2d-image /Users/lalala/learn/anime-arsenal/创作区/制漫剧/金睛缉妖录 第1集`
- 备注：image_qc=block，hard_blocks=52；先修复报告阻断并重跑 image_qc：/Users/lalala/learn/anime-arsenal/创作区/制漫剧/金睛缉妖录/生产数据/image_qc/第1集/image_qc_第1集.md

## 图片质检环境与阶段跳转
- 机检能力：`degraded`
- 当前解释器：`/Applications/Xcode.app/Contents/Developer/usr/bin/python3`
- 当前 image_qc：`verdict=block`，硬阻断 `52`，非阻断初筛 `28`，降级 `True`
- block 摘要：崩脸 G1: 图片/Clip01_end.png | 崩脸 G1: 图片/Clip01_first.png | 崩脸 G1: 图片/Clip01_mid.png
- 当前应停在/回退：`image` — 视觉质检为降级结果，正式进 video 前需补依赖重跑到 full 精度
- 建议安装：优先用 facefusion conda env：/opt/homebrew/Caskroom/miniforge/base/envs/facefusion/bin/python -m pip install pillow opencv-python onnxruntime insightface scikit-image；首次跑 FaceAnalysis(name='buffalo_l') 预热/下载模型。若无该 env，用 Python 3.10-3.12 conda env；系统 Python 3.14 不作为重视觉依赖首选。
- 报告：`/Users/lalala/learn/anime-arsenal/创作区/制漫剧/金睛缉妖录/生产数据/image_qc/第1集/image_qc_第1集.md`

## 健康检测（源/三帧/图片/契约继承）
- **源小说**：✅ 源未变动
- **三帧契约**：豁免（后端 `deferred` 不支持≥3帧·能力门控）
- **图片一致性**：⚠️ hard_blocks=52（verdict=`block`，精度 `degraded`）

## 执行步骤
1. `queue_bounded_rerun`
```bash
python3 skills/n2d-batch/scripts/queue.py plan "/Users/lalala/learn/anime-arsenal/创作区/制漫剧/金睛缉妖录" --episodes 1 --rerun-from script_stage1 --scope "skill 更新后重制到 image" --max-concurrency 1 --max-retries 1
```
2. `manual_alternative`：排队后由 n2d-batch runner 或对应 stage skill 执行返工；不要同时手工运行阶段命令，避免队列账本与实际产物分叉。 手工替代路径仅在不使用 batch 时执行：`n2d-script /Users/lalala/learn/anime-arsenal/创作区/制漫剧/金睛缉妖录 第1集`
3. `verify_after_image_regen`
   - 运行条件：仅在 n2d-batch/阶段 skill 已实际完成图片重出后运行；只生成队列计划时不要当作已验收。
```bash
python3 skills/n2d-dashboard/scripts/dashboard.py gate "/Users/lalala/learn/anime-arsenal/创作区/制漫剧/金睛缉妖录" 第1集 --stage image  # 重出图后验像素一致性（含 image_qc）
```

## 备注
- 真正执行前先看 diff/计划；涉及出图/出视频/配音/合成等付费或不可逆步骤时必须再次确认。
- 共享定妆库需复核（非默认沿用）：本次变更命中定妆库生产规则（skills/n2d-image/SKILL.md, skills/n2d-image/references/prompt_format.md）。先按最新规则复核、必要时重出共享定妆/场景，再用 `python3 skills/n2d-image/scripts/asset_impact.py <作品根> <改动的定妆资产>` 级联出引用它、需跟着重出的本集分镜。
- 三帧契约豁免：路由后端 deferred 不支持≥3帧（能力门控自动豁免），本集不强制中段锚帧。
- 图片一致性存在硬阻断（image_qc verdict=block，hard_blocks=52）：见 `/Users/lalala/learn/anime-arsenal/创作区/制漫剧/金睛缉妖录/生产数据/image_qc/第1集/image_qc_第1集.md`，崩脸/服装/场景/接缝需重出受影响镜。
