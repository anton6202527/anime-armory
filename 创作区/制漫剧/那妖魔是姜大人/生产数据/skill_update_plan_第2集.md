# skill 更新重制计划 — 第2集

- 作品根：`/Users/wesley/learn/anime-armory/创作区/制漫剧/那妖魔是姜大人`
- 当前阶段：`script_stage2`
- 建议动作：`只重跑 gate/review` · `gate/review` → `script_stage2`
- 需要重制：否
- 重制策略：`最小`
- 变动 skill：n2d, n2d-dashboard

## 变动文件
- `skills/n2d-dashboard/scripts/dashboard.py`
- `skills/n2d/SKILL.md`
- `skills/n2d/progress.py`
- `skills/n2d/run.py`
- `skills/n2d/scripts/release_verdict.py`

## 当前生产缺口
- 当前待办：`阶段2·分镜设计`（分镜设计 = `⬜`）
- 建议 skill：`n2d-script`
- 建议命令：`n2d-script /Users/wesley/learn/anime-armory/创作区/制漫剧/那妖魔是姜大人 第2集  (配音后定稿)`

## 健康检测（源/三帧/图片/契约继承）
- **源小说**：✅ 源未变动

## 执行步骤
1. `self_audit`
```bash
python3 skills/n2d-review/scripts/self_audit.py --json
```

## 备注
- 变动集中在 n2d/_lib/review/dashboard/batch/n2d 等横切层，或只涉及该集尚未到达的阶段文件；先重跑 gate/审查/计划，不默认重抽图。
