---
name: song-update
description: 写歌(song) skill 更新影响扫描与最小返工计划器。Use when the user says 更新/update/skill升级/返工/重跑/重审/重评 for a song project, asks whether changed song skills affect an existing song project, or wants a safe plan before rerunning lyrics/compose/cover/review/handoff. It reads `_进度.md`, compares current song skill file content against a stored content snapshot, writes `生产数据/song_skill_update_plan.{json,md}`, and never changes lyrics/audio or `_进度.md`. Triggers song-update, 写歌更新, 歌曲更新, skill更新, 检查更新, 更新影响, 返工计划, 重审计划, 重评计划.
---

# song-update — skill 更新影响扫描 + 最小返工计划

`song-update` 是写歌线的更新影响入口。它只做确定性分析：记录/对比本线 skill 文件内容快照，判断已有歌曲项目是否需要返工，并生成最小计划。它不改歌词、不改音频、不登记 take、不回写 `_进度.md`。

## 输入 / 输出 / 读写边界

- **输入**：`创作区/写歌/<曲名>/_进度.md`、本线 `skills/song*` 文件、项目内上次 `record` 的内容快照。
- **输出**：
  - `record` 或 `check` 自动 bootstrap 写 `生产数据/song_skill_update_snapshot.json`
  - `check --write-plan` 写 `生产数据/song_skill_update_plan.json`
  - `check --write-plan` 写 `生产数据/song_skill_update_plan.md`
- **读写边界**：只写快照和计划；不改歌词、音频、take manifest 或 `_进度.md`。

## 快速使用

```bash
python3 skills/song/song-update/scripts/update_plan.py check "<歌曲项目根>" --write-plan
python3 skills/song/song-update/scripts/update_plan.py record "<歌曲项目根>"
python3 skills/song/song-update/scripts/update_plan.py check "<歌曲项目根>" --json
```

- `record`：阶段产物验收通过后，记录当前 song skill 内容基线。
- `check`：对比基线和当前 skill 文件；无基线时默认建立临时基线并提示确认后 `record` 固化。
- `--no-bootstrap`：无基线时不写盘，只提示需要 `record`。
- `--write-plan`：写计划 JSON/Markdown。
- `--json`：把计划 JSON 打到 stdout。

## 原则

- **不默认整首重做**：只回放到项目已经到达的阶段；尚未开始的未来阶段只提示后续使用新 skill。
- **嵌套子 skill 正确归属**：`skills/song/song-compose/...` 等路径按真实子 skill 映射到阶段，`_lib`/总入口才归 `song`，避免所有变化误判为 setup。
- **安全可逆回放默认继续**：免费、确定性、版本化且不改合同的最小回放直接执行；只在阶段预算创建/扩大/过期、权利缺口、不可逆覆盖或最终真人验收时暂停。
- **计划写入耐崩溃**：快照与 JSON/Markdown 计划使用同目录唯一临时文件、文件 `fsync`、原子替换和目录 `fsync`，并发任务不共享固定 `.tmp`。
- **默认保留旧产物**：计划默认以新路径/新版本回放并保留当前歌词、take 和成品音频；只有执行会覆盖已验收内容、改变核心创作合同或扩大预算时才停下确认。
- **控制面变化不触发返工**：`song-progress`、`song-update` 本身变化只提示刷新进度/更新基线。
- **合规不降级**：涉及换声或真人音色时，仍按授权闸门处理；本 skill 只给计划，不替代合规判断。

## 收尾

跑完 `check` 后，把计划摘要和机器可消费的下一步交给外层编排：变更 skill、是否建议返工、从哪个阶段到哪个阶段、下一步要进哪个 `song-*` skill。本 skill 仍只写计划；外层可自动派发免费、可逆且不覆盖已验收产物的步骤，遇版权/合规、当前音频或最终验收、不可逆覆盖/发布、预算创建/扩大/过期或合同变化时才停。验收通过后跑：

```bash
python3 skills/song/song-update/scripts/update_plan.py record "<歌曲项目根>"
```
