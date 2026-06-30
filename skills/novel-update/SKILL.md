---
name: novel-update
description: 写小说(novel) skill 更新影响扫描与最小文本返工计划器。Use when the user says 更新/update/skill升级/返工/重跑/重审/重评 for a novel project, asks whether changed novel skills affect an existing writing project, or wants a safe plan before rerunning review/score/export. It reads `_进度.md`, compares current novel skill file content against a stored content snapshot, writes `生产数据/novel_skill_update_plan.{json,md}`, and never changes story text or `_进度.md`. Triggers novel-update, 小说更新, skill更新, 检查更新, 更新影响, 返工计划, 重审计划, 重评计划.
---

# novel-update — skill 更新影响扫描 + 最小文本返工计划

`novel-update` 是 novel 线的更新影响入口。它只做确定性分析，不直接写正文、不重审、不重评、不导出，也不回写 `_进度.md`。

它解决的问题：

1. 读 `<作品根>/_进度.md`，判断项目已经产出到哪个文本阶段。
2. 读取上次记录的 novel skill 内容快照；快照是文件内容 SHA256 表，不依赖版本控制。
3. 对比当前 `skills/novel*` 相关文件，找出变化属于正文生产、审稿、评分、导出，还是只影响控制台/进度/调度。
4. 生成最小返工计划：从最早受影响阶段回放，最多只到项目已到达的阶段；尚未开始的未来阶段不要求返工。
5. 把计划写到 `生产数据/novel_skill_update_plan.json` 和 `.md`，等用户确认后再交给对应 novel skill 或 `novel-batch` 执行。

## 输入 / 输出 / 读写边界

- **输入**：`_进度.md`、`skills/novel*` 相关文件、上次 `record` 的内容快照、QA gate 状态。
- **输出**：
  - `record` 或 `check --bootstrap` 写 `生产数据/novel_skill_update_snapshot.json`
  - `check --write-plan` 写 `生产数据/novel_skill_update_plan.json`
  - `check --write-plan` 写 `生产数据/novel_skill_update_plan.md`
- **读写边界**：普通 `check` 只读；显式 `record` / `--bootstrap` / `--write-plan` 才写快照和计划；不改正文、不删产物、不改 `_进度.md`。

## 快速使用

```bash
python3 skills/novel-update/scripts/update_plan.py check "<作品根>" --write-plan
python3 skills/novel-update/scripts/update_plan.py record "<作品根>"
python3 skills/novel-update/scripts/update_plan.py check "<作品根>" --json
```

- `record`：在一轮阶段产物验收通过后，记录当前 novel skill 内容基线。
- `check`：对比基线和当前 skill 文件，生成是否需要返工的判断。
- `--write-plan`：写计划 JSON/Markdown。
- `--json`：把计划 JSON 打到 stdout，供其它工具读取。
- `--bootstrap`：无基线时显式建立一份临时基线并输出 `baseline_bootstrapped=true`；普通 `check` 不写盘。
- 无基线时，普通 `check` 会输出 `needs_record=true`；确认现有产物可接受后，跑 `record` 固化。

## 阶段原则

- **不默认全书返工**：只回放到项目已经到达的阶段。比如项目只写到正文初稿，评分 skill 的变化不会要求现在重评。
- **正文变更先留分支或备份**：若计划从大纲、细纲、正文初稿、改写等会影响正文的阶段回放，执行前先用 `novel-craft/scripts/story_vcs.py` 或项目既有归档方式保留当前文本。
- **审稿/评分报告看新鲜度**：计划会读取 QA gate 摘要；若 review/score 报告绑定的正文快照已过期，先重审或重评，再决定是否改稿。
- **控制面变化不触发正文返工**：`novel-progress`、`novel-dashboard`、`novel-supervisor`、`novel-batch`、`novel-update` 本身变化时，计划只提示重跑看板/调度或更新基线，不要求改正文。

## 输出解读

- `changed_files`：相对仓库根的变动文件。
- `changed_skills`：变动涉及的 novel skill。
- `newly_relevant_skills`：项目阶段推进后首次进入快照范围的 skill，不算旧产物变更。
- `current_stage`：更新影响上界，即项目已经产出到的最远阶段。
- `current_todo`：当前生产前沿，来自 `_进度.md` 的首个未完成项。
- `rebuild_needed`：是否建议返工。
- `rerun_from` / `rerun_until`：建议回放起点和终点。
- `qa_gate`：当前 QA gate 阻断摘要；它帮助判断旧 review/score/export 是否已过期。
- `execution_steps`：建议执行步骤；`type=command` 可直接运行，`type=agent_step` 需要 AI/人判断后执行。

## 收尾必做

跑完 `check` 后，把计划摘要告诉用户，尤其是：

- 变更 skill；
- 是否需要返工；
- 若需要，从哪个阶段到哪个阶段；
- 是否有 QA gate 阻断；
- 下一步是否先备份正文、重跑 review/score/export，或只 `record` 接受当前基线。

用户确认返工后再调用对应 skill 或 `novel-batch`。返工验收通过后，必须跑：

```bash
python3 skills/novel-update/scripts/update_plan.py record "<作品根>"
```

## 常见错误

| 错误 | 纠正 |
|---|---|
| `check` 发现变化就直接改稿 | 本 skill 只产计划；改稿前必须确认范围并保留当前文本 |
| 把未来阶段变化当成立刻返工 | 未来阶段尚未产物化，只提示后续使用新 skill，不要求现在重跑 |
| 无基线时认为没有风险 | 普通 `check` 会提示 `needs_record=true`；只有显式 `--bootstrap` 才建立临时基线，确认现状后应立即 `record` |
