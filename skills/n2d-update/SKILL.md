---
name: n2d-update
description: 制漫剧(novel2drama) skill 更新影响扫描与重制计划器。Use when the user says 更新/重制/update/rebuild/refresh 某个 n2d 作品或某集，or asks whether updated n2d skills require rerunning work. It reads `_进度.md`, detects relevant `skills/` changes against a stored snapshot, plans the minimum safe rerun only up to the episode's current progress stage, writes `生产数据/skill_update_plan_第N集.{json,md}`, and tells the user what to re-run before any paid generation.
---

# n2d-update — skill 更新影响扫描 + 最小重制计划

这是制漫剧线的**更新/重制调度 skill**。它不直接调用生图、生视频、配音或合成后端；它先做确定性分析：

1. 读 `<作品根>/_进度.md` 判断指定集已经走到哪一步。
2. 计算到当前阶段为止相关 n2d skills 的文件指纹。
3. 与上次记录的 skill 快照比对，找出改过的 skill。
4. 生成“从哪一阶段回放、最多重制到哪一阶段、哪些产物需要 diff/复核”的计划。
5. 付费/不可逆步骤只给计划和队列建议，必须等用户确认后再交给对应 stage skill 或 `n2d-batch`。

## 输入 / 输出 / 读写边界

- **输入**：`_进度.md`、当前 `skills/` 文件指纹、上次记录的 skill snapshot、指定集当前前沿。
- **输出**：`生产数据/skill_update_plan_第N集.json/md` 和 skill snapshot 记录。
- **读写边界**：只写更新影响计划和基线；不删除旧产物、不重跑阶段、不改 `_进度.md`。
- **契约关系**：阶段顺序、当前前沿和最多重制范围来自 `skills/common/n2d_contract.py`，避免把 stage 映射写散。

## 快速使用

```bash
python3 skills/n2d-update/scripts/update_plan.py check <作品根> 第1集 --write-plan
python3 skills/n2d-update/scripts/update_plan.py record <作品根> 第1集
python3 skills/n2d-update/scripts/update_plan.py check <作品根> --all --write-plan
```

- `record`：在一次阶段完成、用户接受现状、或完成重制后，记录当前 skill 快照为基线。
- `check`：对比基线；若相关 skill 变了，输出是否建议重制。
- `--write-plan`：写入 `生产数据/skill_update_plan_第N集.json` 和 `.md`，供人审或后续排队。
- `--all`：扫描 `_进度.md` 里所有集。

## 重制原则

- **不默认整集全链重跑**：只回放到该集已经到达的阶段。例如第1集还在出图 `57/68`，最多重制到 `image`，不会主动跑视频或成片。
- **先 diff，再执行**：重制计划里列出受影响 skill 和应复核产物；先让用户看计划，再决定是否排 `n2d-batch` 或人工执行对应 stage skill。
- **从最早受影响阶段开始**：`n2d-script` 变了且当前已到出图，就从分镜/脚本侧复核起；`n2d-image` 变了且当前在出图，就从出图 prompt/image gate 起；只有 `n2d-review`/`n2d-dashboard` 变了，一般先重跑 gate/审查，不重抽图。
- **保留旧产物**：真正重制前，执行者应把将被替换的图/视频/计划移入 `废料/` 或按 stage skill 既有归档规则处理，不能直接覆盖无痕。

## 主动提示

进入已有 n2d 作品时，推荐在 `novel2drama` 源新鲜度检查之后追加一次：

```bash
python3 skills/n2d-update/scripts/update_plan.py check <作品根> <集号> --write-plan
```

如果输出 `rebuild_needed=true`，先提示用户：

> 相关 n2d skills 已变化。当前第N集走到 `<target_stage>`，建议只重制到这个阶段；我已生成计划，是否按计划执行？

用户确认后，再按计划调 `n2d-batch` 或对应 stage skill。

## 输出解读

脚本会输出并写入：

- `changed_files`：相对仓库根的变动 skill 文件。
- `changed_skills`：受影响 skill 名。
- `current_stage`：该集当前生产前沿。
- `rerun_from`：建议回放起点。
- `rerun_until`：最多重制到的阶段，永远不超过该集当前进度。
- `commands`：建议命令；默认是人/agent 可读，不会自动执行。

无基线时，`check` 会给出 `needs_record=true`。首次可先 `record` 建立基线；若 git 工作区已有相关 skill 改动，脚本也会把它们列入提示，方便当前这类“skills 已更新”的场景。

## 常见错误

| 错误 | 纠正 |
|---|---|
| 不等用户确认直接开跑重制 | 本 skill 仅提供最小范围的“重制计划”。实际运行必须先跟用户沟通，再交由 `n2d-batch` 执行 |
| 把更新提醒当成生产故障 | `rebuild_needed=true` 只是提示 skill 有新逻辑升级，并不意味着旧产物已经坏掉 |
| 重制前没有先清理原产物 | 要提醒执行方先移除或归档将被替换的“废料”，以防发生重叠或残留 |
