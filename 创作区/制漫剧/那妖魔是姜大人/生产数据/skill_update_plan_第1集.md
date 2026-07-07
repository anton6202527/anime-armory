# skill 更新重制计划 — 第1集

- 作品根：`/Users/wesley/learn/anime-armory/创作区/制漫剧/那妖魔是姜大人`
- 当前阶段：`review`
- 建议动作：`只重跑 gate/review` · `gate/review` → `review`
- 需要重制：否
- 重制策略：`最小`

## 当前生产缺口
- 当前待办：`审查验收`（验收 = `⬜`）
- 建议 skill：`n2d-review`
- 建议命令：`n2d-review /Users/wesley/learn/anime-armory/创作区/制漫剧/那妖魔是姜大人 第1集`

## 图片质检环境与阶段跳转
- 机检能力：`full`
- 当前解释器：`/opt/homebrew/Caskroom/miniforge/base/envs/facefusion/bin/python`
- 当前 image_qc：`verdict=review`，硬阻断 `0`，非阻断初筛 `71`，降级 `False`
- block 摘要：CHAR_01__囚犯初醒态 跨集脸漂：第1集(均值0.4057)→第2集(均值0.4461)，相对基线掉幅 -0.0404，且本集均值低于绝对下限——已系统性偏离定妆锚 | 片内时序(N2)
- 当前应停在/回退：`video` — full image_qc 仅有非阻断初筛项，已作为 gate warn 入账；不阻断进入 video
- 建议安装：无需补装
- 报告：`/Users/wesley/learn/anime-armory/创作区/制漫剧/那妖魔是姜大人/生产数据/image_qc/第1集/image_qc_第1集.md`

## 健康检测（源/三帧/图片/契约继承）
- **源小说**：✅ 源未变动
- **三帧契约**：豁免（后端 `deferred_auto_route` 不支持≥3帧·能力门控）
- **图片一致性**：✅ 无硬阻断（verdict=`review`，精度 `full`）
- **契约继承**：✅ 已继承（verdict=`pass`）

## 备注
- 三帧契约豁免：路由后端 deferred_auto_route 不支持≥3帧（能力门控自动豁免），本集不强制中段锚帧。
