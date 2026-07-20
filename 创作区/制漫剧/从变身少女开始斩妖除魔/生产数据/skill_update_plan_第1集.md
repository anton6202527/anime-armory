# skill 更新重制计划 — 第1集

- 作品根：`/Users/wesley/learn/anime-armory/创作区/制漫剧/从变身少女开始斩妖除魔`
- 当前阶段：`image`
- 建议动作：`重制` · `image_prompt` → `image`
- 需要重制：是
- 重制策略：`最小`
- 共享定妆库：默认沿用（定妆照/场景照 PNG 复用，重制只覆盖本集分镜帧）
- 变动 skill：n2d-image

## 变动文件
- `skills/n2d-image/scripts/codex_image_runner.py`

## 当前生产缺口
- 当前待办：`出图返修`（出图 = `51/89`）
- 建议 skill：`n2d-image`
- 建议命令：`n2d-image /Users/wesley/learn/anime-armory/创作区/制漫剧/从变身少女开始斩妖除魔 第1集`
- 备注：image_qc=block，hard_blocks=3；先修复报告阻断并重跑 image_qc：/Users/wesley/learn/anime-armory/创作区/制漫剧/从变身少女开始斩妖除魔/生产数据/image_qc/第1集/image_qc_第1集.md

## 图片质检环境与阶段跳转
- 机检能力：`full`
- 当前解释器：`/opt/homebrew/Caskroom/miniforge/base/envs/facefusion/bin/python`
- 当前 image_qc：`verdict=block`，硬阻断 `3`，非阻断初筛 `9`，降级 `False`
- block 摘要：接触/持有镜缺结构化 interaction_graph；自由文本提示无法稳定约束接触点、身体部位归属与遮挡顺序。 | 接触/持有镜缺结构化 interaction_graph；自由文本提示无法稳定约束接触点、身体部位归属与遮挡顺序。
- 当前应停在/回退：`image` — image_qc 有硬阻断，需修复/重抽受影响镜头后重跑
- 建议安装：无需补装
- 报告：`/Users/wesley/learn/anime-armory/创作区/制漫剧/从变身少女开始斩妖除魔/生产数据/image_qc/第1集/image_qc_第1集.md`

## 健康检测（源/三帧/图片/契约继承）
- **源小说**：✅ 源未变动
- **帧策略合同**：⚠️ 必需执行锚缺失 0/13 Clip；缺尾帧声明 0 Clip；缺 PNG 文件 22 个（普通镜不设默认三帧；backend=`None`）
- **图片一致性**：⚠️ hard_blocks=3（verdict=`block`，精度 `full`）

## 执行步骤
1. `queue_bounded_rerun`
```bash
python3 skills/n2d-batch/scripts/queue.py plan "/Users/wesley/learn/anime-armory/创作区/制漫剧/从变身少女开始斩妖除魔" --episodes 1 --rerun-from image_prompt --scope "skill 更新后重制到 image·复用共享定妆库·只重出本集分镜帧" --max-concurrency 1 --max-retries 1
```
2. `manual_alternative`：排队后由 n2d-batch runner 或对应 stage skill 执行返工；不要同时手工运行阶段命令，避免队列账本与实际产物分叉。 手工替代路径仅在不使用 batch 时执行：`n2d-image /Users/wesley/learn/anime-armory/创作区/制漫剧/从变身少女开始斩妖除魔 第1集`
3. `verify_after_image_regen`
   - 运行条件：仅在 n2d-batch/阶段 skill 已实际完成图片重出后运行；只生成队列计划时不要当作已验收。
```bash
python3 skills/n2d-dashboard/scripts/dashboard.py gate "/Users/wesley/learn/anime-armory/创作区/制漫剧/从变身少女开始斩妖除魔" 第1集 --stage image  # 重出图后验像素一致性（含 image_qc）
```

## 备注
- 真正执行前先看 diff/计划；涉及出图/出视频/配音/合成等付费或不可逆步骤时必须再次确认。
- 共享定妆库默认沿用：本次变更未命中定妆库生产规则（标准三视图/角色一致性/资产注册/LoRA），`出图/共享/图片/` 的定妆照/场景照 PNG 与 identity_registry 复用不重出，重制范围只覆盖本集分镜帧。n2d-image 共享先行硬闸门会跳过已 ✅ 的共享 PNG，直接以其为参考重出分镜。
- 帧策略合同未达标：必需执行锚缺失 0 个 Clip，缺尾帧声明 0 个 Clip，已声明但 PNG 不存在 22 个。普通镜不设默认三帧；这里只报告 E1/R1-R3/显式 opt-in 或尾帧真缺口。回 n2d-script 跑 `anchor_planner.py <作品根> 第1集 --write` 补齐声明，再回 n2d-image 出 `_mid/_aK/_end` 帧。；缺文件样例：出图/第1集/图片/EP01_CLIP03_a1.png, 出图/第1集/图片/EP01_CLIP04_a1.png, 出图/第1集/图片/EP01_CLIP05_a1.png, 出图/第1集/图片/EP01_CLIP05_a2.png
- 图片一致性存在硬阻断（image_qc verdict=block，hard_blocks=3）：见 `/Users/wesley/learn/anime-armory/创作区/制漫剧/从变身少女开始斩妖除魔/生产数据/image_qc/第1集/image_qc_第1集.md`，崩脸/服装/场景/接缝需重出受影响镜。
