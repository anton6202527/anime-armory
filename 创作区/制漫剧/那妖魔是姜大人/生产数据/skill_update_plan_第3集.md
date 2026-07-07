# skill 更新重制计划 — 第3集

- 作品根：`/Users/wesley/learn/anime-armory/创作区/制漫剧/那妖魔是姜大人`
- 当前阶段：`video`
- 建议动作：`重制` · `image_prompt` → `video`
- 需要重制：是
- 重制策略：`最小`
- 共享定妆库：默认沿用（定妆照/场景照 PNG 复用，重制只覆盖本集分镜帧）
- 变动 skill：n2d, n2d-image, n2d-review, n2d-video

## 变动文件
- `skills/n2d-image/scripts/image_prompt_pack.py`
- `skills/n2d-review/SKILL.md`
- `skills/n2d-review/scripts/gate.py`
- `skills/n2d-review/scripts/gate_core.py`
- `skills/n2d-review/scripts/video_face_drift_watch.py`
- `skills/n2d-video/SKILL.md`
- `skills/n2d-video/scripts/video_runner.py`
- `skills/n2d/SKILL.md`

## 当前生产缺口
- 当前待办：`图生视频`（视频 = `3/10`）
- 建议 skill：`n2d-video`
- 建议命令：`n2d-video /Users/wesley/learn/anime-armory/创作区/制漫剧/那妖魔是姜大人 第3集`

## 图片质检环境与阶段跳转
- 机检能力：`full`
- 当前解释器：`/opt/homebrew/Caskroom/miniforge/base/envs/facefusion/bin/python`
- 当前 image_qc：`verdict=review`，硬阻断 `0`，非阻断初筛 `66`，降级 `False`
- block 摘要：发型(H1): 图片/Clip02_mid.png | 接触/持有镜缺结构化 interaction_graph；自由文本提示无法稳定约束接触点、身体部位归属与遮挡顺序。
- 当前应停在/回退：`video` — full image_qc 仅有非阻断初筛项，已作为 gate warn 入账；不阻断进入 video
- 建议安装：无需补装
- 报告：`/Users/wesley/learn/anime-armory/创作区/制漫剧/那妖魔是姜大人/生产数据/image_qc/第3集/image_qc_第3集.md`

## 健康检测（源/三帧/图片/契约继承）
- **源小说**：✅ 源未变动
- **三帧契约**：✅ 达标（10 Clip 全有锚帧/尾帧文件或豁免）
- **图片一致性**：✅ 无硬阻断（verdict=`review`，精度 `full`）
- **契约继承**：✅ 已继承（verdict=`pass`）

## 执行步骤
1. `queue_bounded_rerun`
```bash
python3 skills/n2d-batch/scripts/queue.py plan "/Users/wesley/learn/anime-armory/创作区/制漫剧/那妖魔是姜大人" --episodes 3 --rerun-from image_prompt --scope "skill 更新后重制到 video·复用共享定妆库·只重出本集分镜帧" --max-concurrency 1 --max-retries 1
```
2. `manual_alternative`：排队后由 n2d-batch runner 或对应 stage skill 执行返工；不要同时手工运行阶段命令，避免队列账本与实际产物分叉。 手工替代路径仅在不使用 batch 时执行：`n2d-image /Users/wesley/learn/anime-armory/创作区/制漫剧/那妖魔是姜大人 第3集`
3. `verify_after_image_regen`
   - 运行条件：仅在 n2d-batch/阶段 skill 已实际完成图片重出后运行；只生成队列计划时不要当作已验收。
```bash
python3 skills/n2d-dashboard/scripts/dashboard.py gate "/Users/wesley/learn/anime-armory/创作区/制漫剧/那妖魔是姜大人" 第3集 --stage image  # 重出图后验像素一致性（含 image_qc）
```

## 备注
- 真正执行前先看 diff/计划；涉及出图/出视频/配音/合成等付费或不可逆步骤时必须再次确认。
- 共享定妆库默认沿用：本次变更未命中定妆库生产规则（标准三视图/角色一致性/资产注册/LoRA），`出图/共享/图片/` 的定妆照/场景照 PNG 与 identity_registry 复用不重出，重制范围只覆盖本集分镜帧。n2d-image 共享先行硬闸门会跳过已 ✅ 的共享 PNG，直接以其为参考重出分镜。
