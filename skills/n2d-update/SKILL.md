---
name: n2d-update
description: 制漫剧(n2d) skill 更新影响扫描与重制计划器。Use when the user says 更新/重制update/rebuild/refresh 某个 n2d 作品或某集，or asks whether updated n2d skills require rerunning work. It reads `_进度.md`, detects relevant `skills/` changes against a stored snapshot, plans the minimum safe rerun only up to the episode's reached production stage, writes `生产数据/skill_update_plan_第N集.{json,md}`, and tells the user what to re-run before any paid generation.
---

# n2d-update — skill 更新影响扫描 + 最小重制计划

这是制漫剧线的**更新/重制调度 skill**。它不直接调用生图、生视频、配音或合成后端；它先做确定性分析：

1. 读 `<作品根>/_进度.md` 判断指定集已经走到哪一步。
   - 若前序列仍有小缺口（如 `字幕英` 未补）但后续阶段已经开始（如 `出图 25/35`），更新上界按**已开始的最远阶段**算，避免漏掉已有产物受新 gate/review 逻辑影响的范围。
2. 计算到当前阶段为止相关 n2d skills 的文件指纹。
3. 与上次记录的 skill 快照比对，找出改过的 skill。
4. 生成“从哪一阶段回放、最多重制到哪一阶段、哪些产物需要 diff/复核”的计划。
   - 同时单独写出**当前生产缺口**：即便更新影响上界因已有视频产物算到 `video`，也要从 `_进度.md` 首个未完成项补出“当下该做什么”（如 `出图 69/85 → n2d-image`），避免 update 计划把真实生产前沿藏掉。
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
  - 作品级快照不会因只记录某一集的较早阶段而缩窄历史范围；已纳入过的 skill 会保留，避免第2集 record 覆盖掉第1集视频阶段的基线。
- `check`：对比基线；若相关 skill 变了，输出是否建议重制。
- `--write-plan`：写入 `生产数据/skill_update_plan_第N集.json` 和 `.md`，供人审或后续排队。
- `--all`：扫描 `_进度.md` 里所有集。

## 重制原则

- **不默认整集全链重跑**：只回放到该集已经到达的阶段。例如第1集还在出图 `57/68`，最多重制到 `image`，不会主动跑视频或成片。
- **先 diff，再执行**：重制计划里列出受影响 skill 和应复核产物；先让用户看计划，再决定是否排 `n2d-batch` 或人工执行对应 stage skill。
- **从最早受影响阶段开始**：`n2d-script` 变了且当前已到出图，就从分镜/脚本侧复核起；`n2d-image` 变了且当前在出图，就从出图 prompt/image_preflight/image gate 起；只有 `n2d-review`/`n2d-dashboard` 变了，一般先重跑 gate/审查，不重抽图。对 owner 跨多阶段的 skill（如 `n2d-script`），按变动文件映射到具体阶段——只改分镜侧文件（`finalize_storyboard.py` 等）从 `script_stage2` 起，不回到拆集改编。测试文件（`test_*.py`/`tests/`/`conftest.py`）不计入指纹。
- **保留旧产物**：真正重制前，执行者应把将被替换的图/视频/计划移入 `废料/` 或按 stage skill 既有归档规则处理，不能直接覆盖无痕。
- **重出图必带像素验证步**：重制范围覆盖 `image` 阶段（会重出 PNG）时，计划的建议命令会**自动追加** `dashboard gate --stage image` 作为验证步——该 gate 现已合并出图落档机检 `image_qc`（崩脸/服装/场景/接缝/lint + `CHAR_xx` 合法性），所以"重出图 → 验像素一致性"闭环自动接上，不会出现"重出了图却没人验"。`image` 已过的范围（如只重制 video→compose）不追加。`image_qc` 的硬阻断让 gate 非零，初筛项 warn 交人判。

## 重制策略（选择点 `更新重制策略`）

`build_plan` / `check` 按选择点 `更新重制策略` 决定重制力度，解析顺序走 `skills/n2d/references/选择点与偏好.md`：CLI `--regen-mode` > `<作品根>/_设置.md 更新重制策略` > 默认 `最小`。

- **`最小`（默认·保守）**：现有行为——只回放到该集已到阶段、按变动文件算最小重制范围，不默认整集重出。
- **`严审刷新`（推荐·按最新预期严审旧图）**：本模式不是“尽量保住图片”。当重制范围覆盖 `image` 时，先刷新到最新分镜 / 出图 prompt，再用最新 prompt、gate、QC、review 标准审现有图片；只要旧图不符合最新预期，就舍弃并排入重出。旧名 `保图刷新` 仅作为兼容 alias，读到后也归一为 `严审刷新`。
  1. `n2d-batch queue.py plan --rerun-from <文字阶段>` —— 按最新 skill 刷新文字阶段与出图 prompt，封顶到 `image_prompt`，让最新 prompt 成为审旧图标准；
  2. `image_qc.py --regen-list --strict` —— 对现有图片按最新 prompt/QC 标准严审，block / warn / 降级都先进入候选重出清单；
  3. `shots=$(image_qc.py --affected-shots --strict); [ -n "$shots" ] && queue.py plan --rerun-from image $shots` —— 只把有证据不符合最新标准的镜排进重生成；没有证据才不排；
  4. `dashboard gate --stage image` —— 重出的镜回验像素一致性。
  - **判定线**：旧图不是默认可用。`image_qc --strict` 会把 prompt lint、身份/服装/场景/接缝/锚点门的 block/warn/降级命中都列为候选重出；只有已有 gate/QC/review finding 或显式人工判定确认“符合最新 prompt，且不影响连续性/叙事/画风”，才允许保留旧图。
  - **执行边界**：本 skill 仍只生成计划和建议命令，不直接删图、不直接烧图。执行方重出前要按既有归档规则把被替换图片移入 `废料/` 或 stage skill 的归档位置。

## 主动提示

进入已有 n2d 作品时，推荐在 `n2d` 源新鲜度检查之后追加一次：

```bash
python3 skills/n2d-update/scripts/update_plan.py check <作品根> <集号> --write-plan
```

如果输出 `rebuild_needed=true`，先提示用户：

> 相关 n2d skills 已变化。当前第N集走到 `<target_stage>`，建议只重制到这个阶段；我已生成计划，是否按计划执行？

用户确认后，再按计划调 `n2d-batch` 或对应 stage skill。

## 输出解读

脚本会输出并写入：

- `changed_files`：相对仓库根的变动 skill 文件（只比基线与本次相关范围的交集；基线范围差异不算变更）。
- `changed_skills`：受影响 skill 名。
- `newly_relevant_skills`：阶段推进后首次纳入相关范围的 skill，不计为变更；该阶段完成后 `record` 刷新基线。
  - 例外：新纳入 skill 当前在 git 工作区已有改动（含未跟踪文件）时，仍列入 `changed_files`，因为没有旧基线可证明它不影响本集。
- `current_stage`：用于更新上界的当前阶段；若前序有缺口但后续已有产物，取已开始的最远阶段。
- `current_todo`：当前生产缺口/下一步，来自 `_进度.md` 的首个未完成阶段；它和 `current_stage` 可以不同。例如 `current_stage=video` 表示 update 影响上界，`current_todo=image` 表示当前还应先补图。
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
