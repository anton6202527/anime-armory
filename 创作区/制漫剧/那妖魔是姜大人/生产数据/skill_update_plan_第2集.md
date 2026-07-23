# skill 更新重制计划 — 第2集

- 作品根：`/Users/wesley/learn/anime-armory/创作区/制漫剧/那妖魔是姜大人`
- 当前阶段：`image`
- 建议动作：`重制` · `script_stage1` → `image`
- 需要重制：是
- 重制策略：`最小`
- 共享定妆库：需复核（变更命中定妆库生产规则：skills/n2d-image/SKILL.md）
- 需刷新 gate/QC：是（image）
- 变动 skill：n2d, n2d-image, n2d-review

## 变动文件
- `skills/n2d-image/SKILL.md`
- `skills/n2d-image/scripts/codex_image_runner.py`
- `skills/n2d-image/scripts/image_qc.py`
- `skills/n2d-review/scripts/face_consistency.py`
- `skills/n2d-review/scripts/gates/evidence.py`
- `skills/n2d/SKILL.md`
- `skills/n2d/_lib/n2d_const.py`
- `skills/n2d/_lib/n2d_logic.py`
- `skills/n2d/references/特效镜头/README.md`
- `skills/n2d/references/特效镜头/manifest.json`
- `skills/n2d/references/运镜/README.md`
- `skills/n2d/references/运镜/manifest.json`
- `skills/n2d/run.py`
- `skills/n2d/scripts/effect_reference.py`

## 当前生产缺口
- 当前待办：`出图返修`（出图 = `24/24`）
- 建议 skill：`n2d-image`
- 建议命令：`n2d-image /Users/wesley/learn/anime-armory/创作区/制漫剧/那妖魔是姜大人 第2集`
- 备注：image_qc=block，hard_blocks=85；先修复报告阻断并重跑 image_qc：/Users/wesley/learn/anime-armory/创作区/制漫剧/那妖魔是姜大人/生产数据/image_qc/第2集/image_qc_第2集.md

## 图片质检环境与阶段跳转
- 机检能力：`degraded`
- 当前解释器：`/opt/homebrew/opt/python@3.14/bin/python3.14`
- 当前 image_qc：`verdict=block`，硬阻断 `85`，非阻断初筛 `35`，降级 `True`
- block 摘要：脸部覆盖缺失: 图片/EP02_CLIP01_start.png | 脸部覆盖缺失: 图片/EP02_CLIP01_start_a1.png | 脸部覆盖缺失: 图片/EP02_CLIP01_start_a2.png
- 当前应停在/回退：`image` — 视觉质检为降级结果，正式进 video 前需补依赖重跑到 full 精度
- 建议安装：优先用 facefusion conda env：/opt/homebrew/Caskroom/miniforge/base/envs/facefusion/bin/python -m pip install pillow opencv-python onnxruntime insightface scikit-image；首次跑 FaceAnalysis(name='buffalo_l') 预热/下载模型。若无该 env，用 Python 3.10-3.12 conda env；系统 Python 3.14 不作为重视觉依赖首选。
- 报告：`/Users/wesley/learn/anime-armory/创作区/制漫剧/那妖魔是姜大人/生产数据/image_qc/第2集/image_qc_第2集.md`

## 健康检测（源/三帧/图片/契约继承）
- **源小说**：✅ 源未变动
- **帧策略合同**：✅ 达标（需执行锚 7 Clip；普通镜模式=risk_only）
- **图片一致性**：⚠️ hard_blocks=85（verdict=`block`，精度 `degraded`）
- **契约继承**：✅ 已继承（verdict=`pass`）

## 执行步骤
1. `queue_bounded_rerun`
```bash
python3 skills/n2d-batch/scripts/queue.py plan "/Users/wesley/learn/anime-armory/创作区/制漫剧/那妖魔是姜大人" --episodes 2 --rerun-from script_stage1 --scope "skill 更新后重制到 image" --max-concurrency 1 --max-retries 1
```
2. `manual_alternative`：排队后由 n2d-batch runner 或对应 stage skill 执行返工；不要同时手工运行阶段命令，避免队列账本与实际产物分叉。 手工替代路径仅在不使用 batch 时执行：`n2d-script /Users/wesley/learn/anime-armory/创作区/制漫剧/那妖魔是姜大人 第2集`
3. `verify_after_image_regen`
   - 运行条件：仅在 n2d-batch/阶段 skill 已实际完成图片重出后运行；只生成队列计划时不要当作已验收。
```bash
python3 skills/n2d-dashboard/scripts/dashboard.py gate "/Users/wesley/learn/anime-armory/创作区/制漫剧/那妖魔是姜大人" 第2集 --stage image  # 重出图后验像素一致性（含 image_qc）
```

## 备注
- image_qc 硬阻断已将当前生产阶段从 `video` 拉回 `image`；先做 n2d-image 返修并重跑 image_qc，不进入下游。
- 真正执行前先看 diff/计划；涉及出图/出视频/配音/合成等付费或不可逆步骤时必须再次确认。
- 共享定妆库需复核（非默认沿用）：本次变更命中定妆库生产规则（skills/n2d-image/SKILL.md）。先按最新规则复核、必要时重出共享定妆/场景，再用 `python3 skills/n2d-image/scripts/asset_impact.py <作品根> <改动的定妆资产>` 级联出引用它、需跟着重出的本集分镜。
- 图片一致性存在硬阻断（image_qc verdict=block，hard_blocks=85）：见 `/Users/wesley/learn/anime-armory/创作区/制漫剧/那妖魔是姜大人/生产数据/image_qc/第2集/image_qc_第2集.md`，崩脸/服装/场景/接缝需重出受影响镜。
