# skill 更新重制计划 — 第1集

- 作品根：`/Users/lalala/learn/anime-armory/创作区/制漫剧/仙界闭关小能手`
- 当前阶段：`image`
- 建议动作：`重制` · `image_prompt` → `image`
- 需要重制：是
- 重制策略：`最小`
- 共享定妆库：需复核（变更命中定妆库生产规则：skills/n2d-image/SKILL.md）
- 需刷新 gate/QC：是（image）
- 变动 skill：n2d, n2d-image

## 变动文件
- `skills/n2d-image/SKILL.md`
- `skills/n2d-image/scripts/derive_makeup_pack.py`
- `skills/n2d-image/scripts/image_qc.py`
- `skills/n2d/SKILL.md`

## 当前生产缺口
- 当前待办：`出图prompt`（出图prompt = `⬜`）
- 建议 skill：`n2d-image`
- 建议命令：`n2d-image /Users/lalala/learn/anime-armory/创作区/制漫剧/仙界闭关小能手 第1集`
- 说明：更新影响上界仍按最远已开始产物 `image` 计算；当前待办按进度表首个未完成阶段 `image_prompt` 计算。

## 图片质检环境与阶段跳转
- 机检能力：`full`
- 当前解释器：`/opt/homebrew/Caskroom/miniconda/base/bin/python3`
- 当前 image_qc：`verdict=review`，硬阻断 `0`，非阻断初筛 `6`，降级 `False`
- block 摘要：image_preflight 前置锁版账未通过：style_identity_lock 锁定后文件已变化：出图/共享/identity_registry.json。先用统一修复入口补缺失 lock 草稿、确认锁版或记录解锁/最小返工范围：`python3 skills/n2d/scripts/repair_preflight.py "创作区/制漫剧/仙界闭关小能手" 第1集 --stage image_preflight --write-missing`。 | 前期物料可能已过期：n2d-image 自上次 skill 基线后有改动，可能影响本阶段（image）的输入物料。出图/出视频是花钱且不可逆的步骤——先跑 `python3 skills/n2d-update/scripts/update_plan.py check "创作区/制漫剧/仙界闭关小能手" 第1集` 评估哪些物料需重制；统一修复/预检入口：`python3 skills/n2d/scripts/repair_preflight.py "创作区/制漫剧/仙界闭关小能手" 第1集 --stage image --write-missing`。完成重制或确认接受现状后再 `python3 skills/n2d-update/scripts/update_plan.py record "创作区/制漫剧/仙界闭关小能手" 第1集` 固化新基线。
- 当前应停在/回退：`video` — full image_qc 仅有非阻断初筛项，已作为 gate warn 入账；不阻断进入 video
- 建议安装：无需补装
- 报告：`/Users/lalala/learn/anime-armory/创作区/制漫剧/仙界闭关小能手/生产数据/image_qc/第1集/image_qc_第1集.md`

## 健康检测（源/三帧/图片/契约继承）
- **源小说**：✅ 源未变动
- **帧策略合同**：⚠️ 必需执行锚缺失 0/7 Clip；缺尾帧声明 0 Clip；缺 PNG 文件 9 个（普通镜不设默认三帧；backend=`seedance-2.0`）
- **图片一致性**：✅ 无硬阻断（verdict=`review`，精度 `full`）

## 执行步骤
1. `queue_bounded_rerun`
```bash
python3 skills/n2d-batch/scripts/queue.py plan "/Users/lalala/learn/anime-armory/创作区/制漫剧/仙界闭关小能手" --episodes 1 --rerun-from image_prompt --scope "skill 更新后重制到 image" --max-concurrency 1 --max-retries 1
```
2. `manual_alternative`：排队后由 n2d-batch runner 或对应 stage skill 执行返工；不要同时手工运行阶段命令，避免队列账本与实际产物分叉。 手工替代路径仅在不使用 batch 时执行：`n2d-image /Users/lalala/learn/anime-armory/创作区/制漫剧/仙界闭关小能手 第1集`
3. `verify_after_image_regen`
   - 运行条件：仅在 n2d-batch/阶段 skill 已实际完成图片重出后运行；只生成队列计划时不要当作已验收。
```bash
python3 skills/n2d-dashboard/scripts/dashboard.py gate "/Users/lalala/learn/anime-armory/创作区/制漫剧/仙界闭关小能手" 第1集 --stage image  # 重出图后验像素一致性（含 image_qc）
```

## 备注
- 真正执行前先看 diff/计划；涉及出图/出视频/配音/合成等付费或不可逆步骤时必须再次确认。
- 共享定妆库需复核（非默认沿用）：本次变更命中定妆库生产规则（skills/n2d-image/SKILL.md）。先按最新规则复核、必要时重出共享定妆/场景，再用 `python3 skills/n2d-image/scripts/asset_impact.py <作品根> <改动的定妆资产>` 级联出引用它、需跟着重出的本集分镜。
- 帧策略合同未达标：必需执行锚缺失 0 个 Clip，缺尾帧声明 0 个 Clip，已声明但 PNG 不存在 9 个。普通镜不设默认三帧；这里只报告 E1/R1-R3/显式 opt-in 或尾帧真缺口。回 n2d-script 跑 `anchor_planner.py <作品根> 第1集 --write` 补齐声明，再回 n2d-image 出 `_mid/_aK/_end` 帧。；缺文件样例：出图/第1集/图片/EP01_CLIP02_a1.png, 出图/第1集/图片/EP01_CLIP02_a2.png, 出图/第1集/图片/EP01_CLIP03_a1.png, 出图/第1集/图片/EP01_CLIP04_a1.png
