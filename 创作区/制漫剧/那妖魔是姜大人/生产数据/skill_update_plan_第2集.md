# skill 更新重制计划 — 第2集

- 作品根：`/Users/wesley/learn/anime-armory/创作区/制漫剧/那妖魔是姜大人`
- 当前阶段：`video`
- 建议动作：`只重跑 gate/review` · `gate/review` → `video`
- 需要重制：否
- 重制策略：`最小`
- 变动 skill：n2d

## 变动文件
- `skills/n2d/SKILL.md`
- `skills/n2d/_lib/production_mode_router.py`
- `skills/n2d/references/选择点与偏好.md`

## 当前生产缺口
- 当前待办：`视频prompt`（视频prompt = `done`）
- 建议 skill：`n2d-video`
- 建议命令：`n2d-video /Users/wesley/learn/anime-armory/创作区/制漫剧/那妖魔是姜大人 第2集`
- 说明：更新影响上界仍按最远已开始产物 `video` 计算；当前待办按进度表首个未完成阶段 `video_prompt` 计算。

## 图片质检环境与阶段跳转
- 机检能力：`full`
- 当前解释器：`/opt/homebrew/Caskroom/miniforge/base/envs/facefusion/bin/python`
- 当前 image_qc：`verdict=review`，硬阻断 `0`，非阻断初筛 `30`，降级 `False`
- block 摘要：服装配色(N1): 图片/Clip05_end.png | 服装配色(N1): 图片/Clip07_end.png
- 当前应停在/回退：`video` — full image_qc 仅有非阻断初筛项，已作为 gate warn 入账；不阻断进入 video
- 建议安装：无需补装
- 报告：`/Users/wesley/learn/anime-armory/创作区/制漫剧/那妖魔是姜大人/生产数据/image_qc/第2集/image_qc_第2集.md`

## 健康检测（源/三帧/图片/契约继承）
- **源小说**：✅ 源未变动
- **帧策略合同**：✅ 达标（需执行锚 7 Clip；普通镜模式=risk_only）
- **图片一致性**：✅ 无硬阻断（verdict=`review`，精度 `full`）
- **契约继承**：✅ 已继承（verdict=`pass`）

## 执行步骤
1. `refresh_gate`
```bash
python3 skills/n2d-dashboard/scripts/dashboard.py gate "/Users/wesley/learn/anime-armory/创作区/制漫剧/那妖魔是姜大人" 第2集 --stage video
```
2. `refresh_review_findings`
```bash
python3 skills/n2d-review/scripts/consistency_audit.py "/Users/wesley/learn/anime-armory/创作区/制漫剧/那妖魔是姜大人" 第2集  # 刷新 review findings；不重制产物
```

## 备注
- 变动集中在 n2d/_lib/review/dashboard/batch/n2d 等横切层，或只涉及该集尚未到达的阶段文件；先重跑 gate/审查/计划，不默认重抽图。
- 图片一致性报告已过期（image_qc 之后出图被重生成，inputs_fingerprint 失配）：当前结论不可信，先重跑 `python3 skills/n2d-image/scripts/image_qc.py <作品根> 第2集` 再据此判断。
- 契约继承报告已过期（生成后出图/出视频 prompt 又改了，inputs_fingerprint 失配）：`inherited` 结论不可信，先重跑 `python3 skills/n2d-video/scripts/inherit_contract.py <作品根> 第2集` 再判。
