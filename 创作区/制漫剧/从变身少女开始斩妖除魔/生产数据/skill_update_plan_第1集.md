# skill 更新重制计划 — 第1集

- 作品根：`/Users/lalala/learn/anime-armory/创作区/制漫剧/从变身少女开始斩妖除魔`
- 当前阶段：`image`
- 建议动作：`重制` · `script_stage1` → `image`
- 需要重制：是
- 重制策略：`最小`
- 共享定妆库：需复核（变更命中定妆库生产规则：skills/n2d-image/SKILL.md）
- 需刷新 gate/QC：是（image）
- 变动 skill：n2d, n2d-dashboard, n2d-image, n2d-review, n2d-script

## 变动文件
- `skills/n2d-dashboard/scripts/dashboard.py`
- `skills/n2d-image/SKILL.md`
- `skills/n2d-image/scripts/codex_image_runner.py`
- `skills/n2d-image/scripts/cover_pack.py`
- `skills/n2d-image/scripts/derive_makeup_pack.py`
- `skills/n2d-image/scripts/dreamina_image_runner.py`
- `skills/n2d-image/scripts/image_prompt_pack.py`
- `skills/n2d-image/scripts/image_qc.py`
- `skills/n2d-review/SKILL.md`
- `skills/n2d-review/references/production_acceptance_v2.md`
- `skills/n2d-review/scripts/face_consistency.py`
- `skills/n2d-review/scripts/gate_core.py`
- `skills/n2d-review/scripts/gates/backend.py`
- `skills/n2d-review/scripts/identity_eval_pack.py`
- `skills/n2d-review/scripts/production_consistency.py`
- `skills/n2d-script/references/formats.md`
- `skills/n2d-script/scripts/split_novel.py`
- `skills/n2d-script/scripts/story_quality_pack.py`
- `skills/n2d/SKILL.md`
- `skills/n2d/_lib/fixtures/image_prompt_compiler_golden.json`
- `skills/n2d/_lib/image_prompt_compiler.py`
- `skills/n2d/_lib/series_consistency.py`
- `skills/n2d/_lib/settings.py`
- `skills/n2d/_lib/work_card_meta.py`
- `skills/n2d/references/选择点与偏好.md`
- `skills/n2d/run.py`

## 当前生产缺口
- 当前待办：`出图`（出图 = `33/78`）
- 建议 skill：`n2d-image`
- 建议命令：`n2d-image /Users/lalala/learn/anime-armory/创作区/制漫剧/从变身少女开始斩妖除魔 第1集`

## 图片质检环境与阶段跳转
- 机检能力：`full`
- 当前解释器：`/opt/homebrew/Caskroom/miniforge/base/envs/facefusion/bin/python`
- 当前 image_qc：`verdict=review`，硬阻断 `0`，非阻断初筛 `1`，降级 `True`
- block 摘要：identity_eval_pack 缺当前 identity_registry_sha256 或指纹已过期；定妆/形态/档位改动后必须重建验收包。 | 接触/持有镜缺结构化 interaction_graph；自由文本提示无法稳定约束接触点、身体部位归属与遮挡顺序。
- 当前应停在/回退：`video` — full image_qc 仅有非阻断初筛项，已作为 gate warn 入账；不阻断进入 video
- 建议安装：无需补装
- 报告：`/Users/lalala/learn/anime-armory/创作区/制漫剧/从变身少女开始斩妖除魔/生产数据/image_qc/第1集/image_qc_第1集.md`

## 健康检测（源/三帧/图片/契约继承）
- **源小说**：✅ 源未变动
- **帧策略合同**：⚠️ 必需执行锚缺失 0/13 Clip；缺尾帧声明 0 Clip；缺 PNG 文件 24 个（普通镜不设默认三帧；backend=`None`）
- **图片一致性**：✅ 无硬阻断（verdict=`review`，精度 `full`）

## 执行步骤
1. `queue_bounded_rerun`
```bash
python3 skills/n2d-batch/scripts/queue.py plan "/Users/lalala/learn/anime-armory/创作区/制漫剧/从变身少女开始斩妖除魔" --episodes 1 --rerun-from script_stage1 --scope "skill 更新后重制到 image" --max-concurrency 1 --max-retries 1
```
2. `manual_alternative`：排队后由 n2d-batch runner 或对应 stage skill 执行返工；不要同时手工运行阶段命令，避免队列账本与实际产物分叉。 手工替代路径仅在不使用 batch 时执行：`n2d-script /Users/lalala/learn/anime-armory/创作区/制漫剧/从变身少女开始斩妖除魔 第1集`
3. `verify_after_image_regen`
   - 运行条件：仅在 n2d-batch/阶段 skill 已实际完成图片重出后运行；只生成队列计划时不要当作已验收。
```bash
python3 skills/n2d-dashboard/scripts/dashboard.py gate "/Users/lalala/learn/anime-armory/创作区/制漫剧/从变身少女开始斩妖除魔" 第1集 --stage image  # 重出图后验像素一致性（含 image_qc）
```

## 备注
- 真正执行前先看 diff/计划；涉及出图/出视频/配音/合成等付费或不可逆步骤时必须再次确认。
- 共享定妆库需复核（非默认沿用）：本次变更命中定妆库生产规则（skills/n2d-image/SKILL.md）。先按最新规则复核、必要时重出共享定妆/场景，再用 `python3 skills/n2d-image/scripts/asset_impact.py <作品根> <改动的定妆资产>` 级联出引用它、需跟着重出的本集分镜。
- 帧策略合同未达标：必需执行锚缺失 0 个 Clip，缺尾帧声明 0 个 Clip，已声明但 PNG 不存在 24 个。普通镜不设默认三帧；这里只报告 E1/R1-R3/显式 opt-in 或尾帧真缺口。回 n2d-script 跑 `anchor_planner.py <作品根> 第1集 --write` 补齐声明，再回 n2d-image 出 `_mid/_aK/_end` 帧。；缺文件样例：出图/第1集/图片/EP01_CLIP01_a1.png, 出图/第1集/图片/EP01_CLIP02_a1.png, 出图/第1集/图片/EP01_CLIP03_a1.png, 出图/第1集/图片/EP01_CLIP04_a1.png
