# skill 更新重制计划 — 第1集

- 作品根：`/Users/lalala/learn/anime-armory/创作区/制漫剧/仙界闭关小能手`
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
- `skills/n2d-image/scripts/image_prompt_pack.py`
- `skills/n2d-image/scripts/image_qc.py`
- `skills/n2d-review/SKILL.md`
- `skills/n2d-review/references/production_acceptance_v2.md`
- `skills/n2d-review/scripts/identity_eval_pack.py`
- `skills/n2d-review/scripts/production_consistency.py`
- `skills/n2d-script/references/formats.md`
- `skills/n2d-script/scripts/split_novel.py`
- `skills/n2d/SKILL.md`
- `skills/n2d/_lib/fixtures/image_prompt_compiler_golden.json`
- `skills/n2d/_lib/image_prompt_compiler.py`
- `skills/n2d/_lib/settings.py`
- `skills/n2d/_lib/work_card_meta.py`

## 当前生产缺口
- 当前待办：`出图返修`（出图 = `36/51`）
- 建议 skill：`n2d-image`
- 建议命令：`n2d-image /Users/lalala/learn/anime-armory/创作区/制漫剧/仙界闭关小能手 第1集`
- 备注：image_qc=block，hard_blocks=3；先修复报告阻断并重跑 image_qc：/Users/lalala/learn/anime-armory/创作区/制漫剧/仙界闭关小能手/生产数据/image_qc/第1集/image_qc_第1集.md

## 图片质检环境与阶段跳转
- 机检能力：`full`
- 当前解释器：`/opt/homebrew/Caskroom/miniconda/base/bin/python3`
- 当前 image_qc：`verdict=block`，硬阻断 `3`，非阻断初筛 `11`，降级 `False`
- block 摘要：prompt lint:  脸部锚弱信噪比 CHAR_01/本集为14岁杂役常态「face_anchor」（出图/共享/图片/定妆_CHAR_01__本集为14岁杂役常态_表情_六联表.png）：脸占画面仅 2%（建议 ≥30%，核心角教头线 ≥20%）；裁切短边 941px（建议 ≥1024px，核心角教头线 ≥1024px）——弱脸锚会把脸漂带进下游每一镜；核心/长线角色必须重出更紧的脸部特写（脸占 30–50%、≥1024px）后再放行。 | prompt lint:  脸部锚弱信噪比 CHAR_01/本集为14岁杂役常态「face_anchor」（出图/共享/图片/定妆_CHAR_01__本集为14岁杂役常态_表情_六联表.png）：脸占画面仅 2%（建议 ≥30%，核心角教头线 ≥20%）；裁切短边 941px（建议 ≥1024px，核心角教头线 ≥1024px）——弱脸锚会把脸漂带进下游每一镜；核心/长线角色必须重出更紧的脸部特写（脸占 30–50%、≥1024px）后再放行。 | prompt lint:  脸部锚弱信噪比 CHAR_01/本集为14岁杂役常态「六联表」（出图/共享/图片/定妆_CHAR_01__本集为14岁杂役常态_表情_六联表.png）：脸占画面仅 2%（建议 ≥30%，核心角教头线 ≥20%）；裁切短边 941px（建议 ≥1024px，核心角教头线 ≥1024px）——弱脸锚会把脸漂带进下游每一镜；核心/长线角色必须重出更紧的脸部特写（脸占 30–50%、≥1024px）后再放行。
- 当前应停在/回退：`image` — image_qc 有硬阻断，需修复/重抽受影响镜头后重跑
- 建议安装：无需补装
- 报告：`/Users/lalala/learn/anime-armory/创作区/制漫剧/仙界闭关小能手/生产数据/image_qc/第1集/image_qc_第1集.md`

## 健康检测（源/三帧/图片/契约继承）
- **源小说**：✅ 源未变动
- **帧策略合同**：⚠️ 必需执行锚缺失 0/7 Clip；缺尾帧声明 0 Clip；缺 PNG 文件 9 个（普通镜不设默认三帧；backend=`seedance-2.0`）
- **图片一致性**：⚠️ hard_blocks=3（verdict=`block`，精度 `full`）

## 执行步骤
1. `queue_bounded_rerun`
```bash
python3 skills/n2d-batch/scripts/queue.py plan "/Users/lalala/learn/anime-armory/创作区/制漫剧/仙界闭关小能手" --episodes 1 --rerun-from script_stage1 --scope "skill 更新后重制到 image" --max-concurrency 1 --max-retries 1
```
2. `manual_alternative`：排队后由 n2d-batch runner 或对应 stage skill 执行返工；不要同时手工运行阶段命令，避免队列账本与实际产物分叉。 手工替代路径仅在不使用 batch 时执行：`n2d-script /Users/lalala/learn/anime-armory/创作区/制漫剧/仙界闭关小能手 第1集`
3. `verify_after_image_regen`
   - 运行条件：仅在 n2d-batch/阶段 skill 已实际完成图片重出后运行；只生成队列计划时不要当作已验收。
```bash
python3 skills/n2d-dashboard/scripts/dashboard.py gate "/Users/lalala/learn/anime-armory/创作区/制漫剧/仙界闭关小能手" 第1集 --stage image  # 重出图后验像素一致性（含 image_qc）
```

## 备注
- 真正执行前先看 diff/计划；涉及出图/出视频/配音/合成等付费或不可逆步骤时必须再次确认。
- 共享定妆库需复核（非默认沿用）：本次变更命中定妆库生产规则（skills/n2d-image/SKILL.md）。先按最新规则复核、必要时重出共享定妆/场景，再用 `python3 skills/n2d-image/scripts/asset_impact.py <作品根> <改动的定妆资产>` 级联出引用它、需跟着重出的本集分镜。
- 帧策略合同未达标：必需执行锚缺失 0 个 Clip，缺尾帧声明 0 个 Clip，已声明但 PNG 不存在 9 个。普通镜不设默认三帧；这里只报告 E1/R1-R3/显式 opt-in 或尾帧真缺口。回 n2d-script 跑 `anchor_planner.py <作品根> 第1集 --write` 补齐声明，再回 n2d-image 出 `_mid/_aK/_end` 帧。；缺文件样例：出图/第1集/图片/EP01_CLIP02_a1.png, 出图/第1集/图片/EP01_CLIP02_a2.png, 出图/第1集/图片/EP01_CLIP03_a1.png, 出图/第1集/图片/EP01_CLIP04_a1.png
- 图片一致性存在硬阻断（image_qc verdict=block，hard_blocks=3）：见 `/Users/lalala/learn/anime-armory/创作区/制漫剧/仙界闭关小能手/生产数据/image_qc/第1集/image_qc_第1集.md`，崩脸/服装/场景/接缝需重出受影响镜。
- 图片一致性报告已过期（image_qc 之后出图被重生成，inputs_fingerprint 失配）：当前结论不可信，先重跑 `python3 skills/n2d-image/scripts/image_qc.py <作品根> 第1集` 再据此判断。
