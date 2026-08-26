---
name: ad-update
description: 拍广告(ad) skill 更新影响扫描与最小返工计划器。Use when the user says 更新/update/skill升级/返工/重跑/重审/重评 for an ad project, asks whether changed ad skills affect an existing ad project, or wants a safe plan before rerunning brief/concept/script/voice/image/video/compose/review/handoff. It reads `_进度.md`, compares current ad skill file content against a stored content snapshot, writes `生产数据/ad_skill_update_plan.{json,md}`, and never changes ad assets or `_进度.md`. Triggers ad-update, 广告更新, 拍广告更新, skill更新, 检查更新, 更新影响, 返工计划, 重审计划, 重评计划.
---

# ad-update — skill 更新影响扫描 + 最小返工计划

`ad-update` 是广告线的更新影响入口。它只做确定性分析：记录/对比本线 skill 文件内容快照，判断已有广告项目是否需要返工，并生成最小计划。它不改 brief、不改脚本、不配音、不出图、不出视频、不合成、不回写 `_进度.md`。

## 输入 / 输出 / 读写边界

- **输入**：`创作区/拍广告/<项目>/_进度.md`、本线 `skills/ad*` 文件、项目内上次 `record` 的内容快照。
- **输出**：
  - `record` 或 `check` 自动 bootstrap 写 `生产数据/ad_skill_update_snapshot.json`
  - `check --write-plan` 写 `生产数据/ad_skill_update_plan.json`
  - `check --write-plan` 写 `生产数据/ad_skill_update_plan.md`
- **读写边界**：只写快照和计划；不改 brief、脚本、媒体产物、交付矩阵或 `_进度.md`。

## 快速使用

```bash
python3 skills/ad/ad-update/scripts/update_plan.py check "<广告项目根>" --write-plan
python3 skills/ad/ad-update/scripts/update_plan.py record "<广告项目根>"
python3 skills/ad/ad-update/scripts/update_plan.py check "<广告项目根>" --json
```

- `record`：阶段产物验收通过后，记录当前 ad skill 内容基线。
- `check`：对比基线和当前 skill 文件；无基线时默认建立临时基线并提示确认后 `record` 固化。
- `--no-bootstrap`：无基线时不写盘，只提示需要 `record`。
- `--write-plan`：写计划 JSON/Markdown。
- `--json`：把计划 JSON 打到 stdout。

## 原则

- **不默认整条广告重做**：只回放到项目已经到达的阶段；尚未开始的未来阶段只提示后续使用新 skill。
- **嵌套子 skill 正确归属**：`skills/ad/ad-video/...` 等路径按真实子 skill 映射到阶段，`_lib`/总入口才归 `ad`，避免所有变化误判为 brief。
- **安全可逆回放默认继续**：若已有精确有效预算包、输出版本化可恢复且不改 brief/claim 核心合同，最小返工直接继续；预算创建/扩大/过期/绑定变化、权利缺口、不可逆覆盖/发布或最终真人验收才暂停。
- **计划写入耐崩溃**：快照与 JSON/Markdown 计划使用同目录唯一临时文件、文件 `fsync`、原子替换和目录 `fsync`，并发任务不共享固定 `.tmp`。
- **控制面变化不触发返工**：`ad-progress`、`ad-update` 本身变化只提示刷新进度/更新基线。
- **合规不降级**：广告法、claim 依据、肖像/音乐/字体/素材授权仍由广告线 gate 和 review 判断；本 skill 只给计划。

## 收尾

跑完 `check` 后，把计划摘要写入下一动作卡：变更 skill、是否建议返工、从哪个阶段到哪个阶段、下一步要进哪个 `ad-*` skill。若目标 image/video 阶段已有精确匹配且有效的阶段预算包、输出版本化可恢复且不改变 brief/claim 核心合同，调度 agent 可同任务继续；预算包缺失/扩大/过期/绑定变化，或会不可逆覆盖/发布时才请求确认。验收通过后跑：

```bash
python3 skills/ad/ad-update/scripts/update_plan.py record "<广告项目根>"
```
