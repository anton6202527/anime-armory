# skill 更新重制计划 — 第5集

- 作品根：`/Users/wesley/learn/anime-armory/创作区/制漫剧/那妖魔是姜大人`
- 当前阶段：`image`
- 建议动作：`刷新 gate/QC` · `image` → `image`
- 需要重制：否
- 重制策略：`最小`
- 需刷新 gate/QC：是（image）
- 变动 skill：n2d, n2d-image

## 变动文件
- `skills/n2d-image/scripts/image_qc.py`
- `skills/n2d/SKILL.md`

## 当前生产缺口
- 当前待办：`出图返修`（出图 = `94/125`）
- 建议 skill：`n2d-image`
- 建议命令：`n2d-image /Users/wesley/learn/anime-armory/创作区/制漫剧/那妖魔是姜大人 第5集`
- 备注：image_qc=block，hard_blocks=26；先修复报告阻断并重跑 image_qc：/Users/wesley/learn/anime-armory/创作区/制漫剧/那妖魔是姜大人/生产数据/image_qc/第5集/image_qc_第5集.md

## 图片质检环境与阶段跳转
- 机检能力：`full`
- 当前解释器：`/opt/homebrew/Caskroom/miniforge/base/envs/facefusion/bin/python`
- 当前 image_qc：`verdict=block`，硬阻断 `26`，非阻断初筛 `28`，降级 `False`
- block 摘要：脸部覆盖缺失: 图片/Clip05_first.png | 脸部覆盖缺失: 图片/Clip05_first.png | 脸部覆盖缺失: 图片/Clip05_first.png
- 当前应停在/回退：`image` — image_qc 有硬阻断，需修复/重抽受影响镜头后重跑
- 建议安装：无需补装
- 报告：`/Users/wesley/learn/anime-armory/创作区/制漫剧/那妖魔是姜大人/生产数据/image_qc/第5集/image_qc_第5集.md`

## 健康检测（源/三帧/图片/契约继承）
- **源小说**：✅ 源未变动
- **三帧契约**：豁免（后端 `None` 不支持≥3帧·能力门控）
- **图片一致性**：⚠️ hard_blocks=26（verdict=`block`，精度 `full`）

## 执行步骤
1. `refresh_gate`
```bash
python3 skills/n2d-dashboard/scripts/dashboard.py gate "/Users/wesley/learn/anime-armory/创作区/制漫剧/那妖魔是姜大人" 第5集 --stage image
```

## 备注
- 变动集中在 n2d/_lib/review/dashboard/batch/n2d 等横切层，或只涉及该集尚未到达的阶段文件；先重跑 gate/审查/计划，不默认重抽图。
- 三帧契约豁免：路由后端 None 不支持≥3帧（能力门控自动豁免），本集不强制中段锚帧。
- 图片一致性存在硬阻断（image_qc verdict=block，hard_blocks=26）：见 `/Users/wesley/learn/anime-armory/创作区/制漫剧/那妖魔是姜大人/生产数据/image_qc/第5集/image_qc_第5集.md`，崩脸/服装/场景/接缝需重出受影响镜。
