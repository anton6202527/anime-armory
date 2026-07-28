# skill 更新重制计划 — 第3集

- 作品根：`/Users/wesley/learn/anime-armory/创作区/制漫剧/那妖魔是姜大人`
- 当前阶段：`video_prompt`
- 建议动作：`只重跑 gate/review` · `gate/review` → `video_prompt`
- 需要重制：否
- 重制策略：`最小`

## 当前生产缺口
- 当前待办：`视频prompt`（视频prompt = `⬜`）
- 建议 skill：`n2d-video`
- 建议命令：`n2d-video /Users/wesley/learn/anime-armory/创作区/制漫剧/那妖魔是姜大人 第3集`

## 图片质检环境与阶段跳转
- 机检能力：`full`
- 当前解释器：`/opt/homebrew/Caskroom/miniforge/base/envs/facefusion/bin/python`
- 当前 image_qc：`verdict=review`，硬阻断 `0`，非阻断初筛 `16`，降级 `False`
- block 摘要：风格(S1): Clip05_first.png | 天气时辰(W1): Clip07_end.png
- 当前应停在/回退：`video` — full image_qc 仅有非阻断初筛项，已作为 gate warn 入账；不阻断进入 video
- 建议安装：无需补装
- 报告：`/Users/wesley/learn/anime-armory/创作区/制漫剧/那妖魔是姜大人/生产数据/image_qc/第3集/image_qc_第3集.md`

## 健康检测（源/三帧/图片/契约继承）
- **源小说**：✅ 源未变动
- **帧策略合同**：✅ 达标（需执行锚 4 Clip；普通镜模式=risk_only）
- **图片一致性**：✅ 无硬阻断（verdict=`review`，精度 `full`）
- **契约继承**：✅ 已继承（verdict=`pass`）

## 备注
- 契约继承报告已过期（生成后出图/出视频 prompt 又改了，inputs_fingerprint 失配）：`inherited` 结论不可信，先重跑 `python3 skills/n2d-video/scripts/inherit_contract.py <作品根> 第3集` 再判。
