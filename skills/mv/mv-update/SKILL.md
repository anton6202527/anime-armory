---
name: mv-update
description: 制MV(mv) skill 更新影响扫描与最小返工计划器。Use when the user says 更新/update/skill升级/返工/重跑/重审/重评 for an MV project, asks whether changed mv skills affect an existing MV project, or wants a safe plan before rerunning beat/script/plan/image/video/lyric-sync/compose/review. It reads `_进度.md`, compares current mv skill file content against a stored content snapshot, writes `生产数据/mv_skill_update_plan.{json,md}`, and never changes visual/audio/video assets or `_进度.md`. Triggers mv-update, MV更新, 制MV更新, skill更新, 检查更新, 更新影响, 返工计划, 重审计划, 重评计划.
---

# mv-update — skill 更新影响扫描 + 最小返工计划

`mv-update` 是 MV 线的更新影响入口。它只做确定性分析：记录/对比本线 skill 文件内容快照，判断已有 MV 项目是否需要返工，并生成最小计划。它不改蓝图、不改分镜、不出图、不出视频、不合成、不回写 `_进度.md`。

## 输入 / 输出 / 读写边界

- **输入**：`创作区/制MV/<曲名>/_进度.md`、本线 `skills/mv*` 文件、项目内上次 `record` 的内容快照。
- **输出**：
  - `record` 或 `check` 自动 bootstrap 写 `生产数据/mv_skill_update_snapshot.json`
  - `check --write-plan` 写 `生产数据/mv_skill_update_plan.json`
  - `check --write-plan` 写 `生产数据/mv_skill_update_plan.md`
- **读写边界**：只写快照和计划；不改任何视觉、音频、视频产物或 `_进度.md`。

## 快速使用

```bash
python3 skills/mv/mv-update/scripts/update_plan.py check "<MV项目根>" --write-plan
python3 skills/mv/mv-update/scripts/update_plan.py record "<MV项目根>"
python3 skills/mv/mv-update/scripts/update_plan.py check "<MV项目根>" --json
```

- `record`：阶段产物验收通过后，记录当前 mv skill 内容基线。
- `check`：对比基线和当前 skill 文件；无基线时默认建立临时基线并提示确认后 `record` 固化。
- `--no-bootstrap`：无基线时不写盘，只提示需要 `record`。
- `--write-plan`：写计划 JSON/Markdown。
- `--json`：把计划 JSON 打到 stdout。

## 原则

- **不默认整支 MV 重做**：只回放到项目已经到达的阶段；尚未开始的未来阶段只提示后续使用新 skill。
- **触及付费视觉前先确认**：若计划覆盖出图、出视频、合成，先确认后端、规格、预算和保留旧素材策略。
- **控制面变化不触发返工**：`mv-progress`、`mv-update` 本身变化只提示刷新进度/更新基线。
- **后配歌曲路线不越级**：最终音频未入库时，不得把未来正式卡点、正式 timeline、正式出图/出视频当作当前应返工范围。

## 收尾

跑完 `check` 后，把计划摘要告诉用户：变更 skill、是否建议返工、从哪个阶段到哪个阶段、下一步要进哪个 `mv-*` skill。用户确认后再执行；验收通过后跑：

```bash
python3 skills/mv/mv-update/scripts/update_plan.py record "<MV项目根>"
```

