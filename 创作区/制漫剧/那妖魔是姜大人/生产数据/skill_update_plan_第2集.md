# skill 更新重制计划 — 第2集

- 作品根：`/Users/wesley/learn/anime-armory/创作区/制漫剧/那妖魔是姜大人`
- 当前阶段：`image`
- 建议动作：`重制` · `script_stage1` → `image`
- 需要重制：是
- 重制策略：`最小`
- 共享定妆库：需复核（变更命中定妆库生产规则：skills/n2d-image/SKILL.md）
- 需刷新 gate/QC：是（image）
- 变动 skill：n2d, n2d-image, n2d-review, n2d-script

## 变动文件
- `skills/n2d-image/SKILL.md`
- `skills/n2d-image/scripts/codex_image_runner.py`
- `skills/n2d-image/scripts/image_qc.py`
- `skills/n2d-image/scripts/shot_scale_contract.py`
- `skills/n2d-review/scripts/gate.py`
- `skills/n2d-review/scripts/gate_core.py`
- `skills/n2d-review/scripts/gates/contract.py`
- `skills/n2d-review/scripts/gates/scene.py`
- `skills/n2d-script/SKILL.md`
- `skills/n2d-script/references/分镜语法.md`
- `skills/n2d-script/references/拆集法.md`
- `skills/n2d-script/scripts/clip_economy_planner.py`
- `skills/n2d-script/scripts/director_blocking_pack.py`
- `skills/n2d-script/scripts/shot_grammar_audit.py`
- `skills/n2d-script/scripts/shot_split_decision.py`
- `skills/n2d-script/scripts/source_adaptation_audit.py`
- `skills/n2d-script/scripts/story_spine.py`
- `skills/n2d/SKILL.md`
- `skills/n2d/_lib/n2d_const.py`
- `skills/n2d/_lib/n2d_contract_diff.py`
- `skills/n2d/_lib/n2d_insert_coverage.py`
- `skills/n2d/_lib/settings.py`
- `skills/n2d/references/genre_packs/chuanyue.json`
- `skills/n2d/references/选择点与偏好.md`
- `skills/n2d/run.py`
- `skills/n2d/scripts/genre_packs.py`
- `skills/n2d/scripts/preventive_contracts.py`

## 当前生产缺口
- 当前待办：`出图返修`（出图 = `24/24`）
- 建议 skill：`n2d-image`
- 建议命令：`n2d-image /Users/wesley/learn/anime-armory/创作区/制漫剧/那妖魔是姜大人 第2集`
- 备注：image_qc=block，hard_blocks=4；先修复报告阻断并重跑 image_qc：/Users/wesley/learn/anime-armory/创作区/制漫剧/那妖魔是姜大人/生产数据/image_qc/第2集/image_qc_第2集.md

## 图片质检环境与阶段跳转
- 机检能力：`full`
- 当前解释器：`/opt/homebrew/Caskroom/miniforge/base/envs/facefusion/bin/python`
- 当前 image_qc：`verdict=block`，硬阻断 `4`，非阻断初筛 `30`，降级 `False`
- block 摘要：服装配色(N1): 图片/Clip03_end.png | 服装配色(N1): 图片/Clip05_end.png
- 当前应停在/回退：`image` — image_qc 有硬阻断，需修复/重抽受影响镜头后重跑
- 建议安装：无需补装
- 报告：`/Users/wesley/learn/anime-armory/创作区/制漫剧/那妖魔是姜大人/生产数据/image_qc/第2集/image_qc_第2集.md`

## 健康检测（源/三帧/图片/契约继承）
- **源小说**：✅ 源未变动
- **帧策略合同**：✅ 达标（需执行锚 7 Clip；普通镜模式=risk_only）
- **图片一致性**：⚠️ hard_blocks=4（verdict=`block`，精度 `full`）
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
- 图片一致性存在硬阻断（image_qc verdict=block，hard_blocks=4）：见 `/Users/wesley/learn/anime-armory/创作区/制漫剧/那妖魔是姜大人/生产数据/image_qc/第2集/image_qc_第2集.md`，崩脸/服装/场景/接缝需重出受影响镜。
- 契约继承报告已过期（生成后出图/出视频 prompt 又改了，inputs_fingerprint 失配）：`inherited` 结论不可信，先重跑 `python3 skills/n2d-video/scripts/inherit_contract.py <作品根> 第2集` 再判。
