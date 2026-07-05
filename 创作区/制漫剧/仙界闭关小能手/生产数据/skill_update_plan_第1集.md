# skill 更新重制计划 — 第1集

- 作品根：`/Users/lalala/learn/anime-armory/创作区/制漫剧/仙界闭关小能手`
- 当前阶段：`review`
- 建议动作：`只重跑 gate/review` · `gate/review` → `review`
- 需要重制：否
- 重制策略：`最小`
- 变动 skill：n2d, n2d-update
- 新纳入范围（不计变更）：n2d-compose, n2d-lora

## 变动文件
- `skills/n2d-update/SKILL.md`
- `skills/n2d/_lib/skill_freshness.py`

## 当前生产缺口
- 当前待办：`审查验收`（验收 = `⬜`）
- 建议 skill：`n2d-review`
- 建议命令：`n2d-review /Users/lalala/learn/anime-armory/创作区/制漫剧/仙界闭关小能手 第1集`

## 图片质检环境与阶段跳转
- 机检能力：`full`
- 当前解释器：`/opt/homebrew/Caskroom/miniforge/base/envs/facefusion/bin/python`
- 当前 image_qc：`verdict=review`，硬阻断 `0`，非阻断初筛 `103`，降级 `False`
- block 摘要：脸(G1): 图片/Clip13_end.png | 脸(G1): 图片/Clip14_end.png
- 当前应停在/回退：`video` — full image_qc 仅有非阻断初筛项，已作为 gate warn 入账；不阻断进入 video
- 建议安装：无需补装
- 报告：`/Users/lalala/learn/anime-armory/创作区/制漫剧/仙界闭关小能手/生产数据/image_qc/第1集/image_qc_第1集.md`

## 健康检测（源/三帧/图片/契约继承）
- **源小说**：✅ 源未变动
- **三帧契约**：豁免（后端 `None` 不支持≥3帧·能力门控）
- **图片一致性**：✅ 无硬阻断（verdict=`review`，精度 `full`）
- **契约继承**：✅ 已继承（verdict=`pass`）

## 执行步骤
1. `refresh_gate`
```bash
python3 skills/n2d-dashboard/scripts/dashboard.py gate "/Users/lalala/learn/anime-armory/创作区/制漫剧/仙界闭关小能手" 第1集 --stage review
```
2. `refresh_review_findings`
```bash
python3 skills/n2d-review/scripts/consistency_audit.py "/Users/lalala/learn/anime-armory/创作区/制漫剧/仙界闭关小能手" 第1集  # 刷新 review findings；不重制产物
```

## 备注
- n2d-compose, n2d-lora 因阶段推进首次纳入相关范围，本次不计为变更；该阶段完成后请 record 刷新基线。
- 变动集中在 n2d/_lib/review/dashboard/batch/n2d 等横切层，或只涉及该集尚未到达的阶段文件；先重跑 gate/审查/计划，不默认重抽图。
- 三帧契约豁免：路由后端 None 不支持≥3帧（能力门控自动豁免），本集不强制中段锚帧。
- 图片一致性报告已过期（image_qc 之后出图被重生成，inputs_fingerprint 失配）：当前结论不可信，先重跑 `python3 skills/n2d-image/scripts/image_qc.py <作品根> 第1集` 再据此判断。
- 契约继承报告已过期（生成后出图/出视频 prompt 又改了，inputs_fingerprint 失配）：`inherited` 结论不可信，先重跑 `python3 skills/n2d-video/scripts/inherit_contract.py <作品根> 第1集` 再判。
