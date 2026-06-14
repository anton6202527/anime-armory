---
name: n2d-update
description: 制漫剧(n2d) skill 更新影响扫描与重制计划器（含少量图片/视频选择性刷新 `media` 子命令）。Use when the user says 更新/重制/update/rebuild/refresh 某个 n2d 作品或某集，asks whether updated n2d skills require rerunning work, or wants to 只重出部分图片/部分视频. It reads `_进度.md`, detects relevant `skills/` changes against a stored snapshot, plans the minimum safe rerun only up to the episode's reached production stage, writes `生产数据/skill_update_plan_第N集.{json,md}`, and tells the user what to re-run before any paid generation; the `media` 子命令为指定集/指定 Clip 生成证据驱动的选择性刷新计划。Triggers 更新, update, 检查更新, skill升级, 重制计划, 媒体重制, 部分图片重制, 部分视频重制, 只重出部分图片, 只重出部分视频, n2d-update.
---

# n2d-update — skill 更新影响扫描 + 最小重制计划 + 选择性媒体刷新

> **本 skill 是制漫剧线唯一的更新/重制入口（n2d 专用）。** 原跨线 `update` 分发器已于 2026-06 退场——其他创作线暂不需要更新嗅探，媒体选择性刷新作为本 skill 的 `media` 子命令并入。

这是制漫剧线的**更新/重制调度 skill**。它不直接调用生图、生视频、配音或合成后端；它先做确定性分析：

1. 读 `<作品根>/_进度.md` 判断指定集已经走到哪一步。
   - 若前序列仍有小缺口（如 `字幕英` 未补）但后续阶段已经开始（如 `出图 25/35`），更新上界按**已开始的最远阶段**算，避免漏掉已有产物受新 gate/review 逻辑影响的范围。
2. 取到当前阶段为止相关 n2d skills 的基线。基线是 **文件内容快照**：相关 skill 文件逐个内容 SHA256 表（`files`），**不依赖 git 或任何版本控制**——交付到用户端零 VCS 依赖，中文路径也天然无障碍。
3. 重算当前 `skills/` 相关文件内容 SHA 并与基线 `files` 表逐项比对，hash 不同即变更，找出改过的 skill。（旧版 git 派生基线只有 `git_commit`、无内容表，读到时提示用户重新 `record` 建立内容基线。）
4. 生成“从哪一阶段回放、最多重制到哪一阶段、哪些产物需要 diff/复核”的计划。
   - 同时单独写出**当前生产缺口**：即便更新影响上界因已有视频产物算到 `video`，也要从 `_进度.md` 首个未完成项补出“当下该做什么”（如 `出图 69/85 → n2d-image`），避免 update 计划把真实生产前沿藏掉。
5. 付费/不可逆步骤只给计划和队列建议，必须等用户确认后再交给对应 stage skill 或 `n2d-batch`。

除了 skill 变更，`check` 还跑**四项产物健康检测**（写进计划 `source_drift`/`three_frame_compliance`/`image_consistency`/`contract_inheritance`，CLI 打 `health:` 行）：

- **源小说漂移**：跑 `n2d/source_check.py`（有 `小说/_源指纹.json` 基线才跑），写小说成品一改即发现本剧源过期 → 列变动章 + 落在哪些集。重切属不可逆点，只提示不自动切。
- **三帧契约遵循**：读 `脚本/第N集/storyboard.json`，按 `policy.video_backend` 的后端能力判定（能力门控铁律：支持≥3帧的后端强制），列出缺 `midframe/anchors` 且无豁免理由的违规 Clip → 指回 `anchor_planner.py --write` 补齐。后端不支持≥3帧（first-frame-only）则标豁免、不算违规。
- **图片一致性**：从已有 `image_qc` 报告压出崩脸/服装/场景/接缝硬阻断摘要（`hard_blocks`/verdict），有硬阻断则提示重出受影响镜。
- **出图→出视频契约继承**：到 `video_prompt` 阶段后，读 `n2d-video/inherit_contract.py` 的产物 `生产数据/contract_inheritance_第N集.json`，压出 verdict + 字段漂移/身份未锁/资产丢失计数——校验**参考帧契约**（色调/光位锚/轴线视线/角色状态演进/景别）与**文字 prompt** 是否从出图侧正确传到出视频侧、命名角色镜是否锁脸、出图绑定的场景/道具/特效资产是否丢失。本 skill 只读报告不自己跑机检（出视频前的契约门由 n2d-video 把）：已到 `video_prompt` 但**缺报告** → 提示先跑 `inherit_contract.py <作品根> 第N集` 取证；verdict=`block` → 提示先按出图侧原文修 `出视频/prompt` 的视觉契约/身份锚点/物料绑定再出视频。

## 输入 / 输出 / 读写边界

- **输入**：`_进度.md`、当前 `skills/` 相关文件内容、上次记录的 skill snapshot（内容 SHA 快照）、指定集当前前沿。**不读 git 状态。**
- **输出**：`生产数据/skill_update_plan_第N集.json/md` 和 skill snapshot 记录（相关 skill 文件的内容 SHA 表，无版本控制依赖）。
- **读写边界**：只写更新影响计划和基线；不删除旧产物、不重跑阶段、不改 `_进度.md`。
- **契约关系**：阶段顺序、当前前沿和最多重制范围来自 `skills/n2d/_lib/n2d_contract.py`，避免把 stage 映射写散。

## 快速使用

```bash
python3 skills/n2d-update/scripts/update_plan.py check <作品根> 第1集 --write-plan
python3 skills/n2d-update/scripts/update_plan.py record <作品根> 第1集
python3 skills/n2d-update/scripts/update_plan.py check <作品根> --all --write-plan
# 少量图片/视频选择性刷新（证据驱动，不审片）：
python3 skills/n2d-update/scripts/update_plan.py media <作品根> 第1集 --image Clip_001 --video Clip_002 --write-plan
```

- `record`：在一次阶段完成、用户接受现状、或完成重制后，记录当前 skill 基线（相关 skill 文件的内容 SHA 快照）。
  - 作品级快照不会因只记录某一集的较早阶段而缩窄历史范围；已纳入过的 skill 会保留，避免第2集 record 覆盖掉第1集视频阶段的基线。
  - 基线即"record 当刻的文件内容"；记录后这些内容就是新基准，下次 `check` 只报相对它的真实改动。
- `check`：对比基线；若相关 skill 变了，输出是否建议重制。
- `--write-plan`：写入 `生产数据/skill_update_plan_第N集.json` 和 `.md`，供人审或后续排队。
- `--all`：扫描 `_进度.md` 里所有集。
- 计划 JSON 同时写 `execution_steps[]` 与兼容字段 `commands[]`。`execution_steps[]` 是权威：`type=command` 表示可执行命令，`type=agent_step` 表示需 AI/人按条件执行；带 `run_when` 的命令只有条件满足后才跑，不能把整段当作无条件 shell 顺序执行。

## 重制原则

- **不默认整集全链重跑**：只回放到该集已经到达的阶段。例如第1集还在出图 `57/68`，最多重制到 `image`，不会主动跑视频或成片。
- **先 diff，再执行**：重制计划里列出受影响 skill 和应复核产物；先让用户看计划，再决定是否排 `n2d-batch` 或人工执行对应 stage skill。
- **从最早受影响阶段开始**：`n2d-script` 变了且当前已到出图，就从分镜/脚本侧复核起；`n2d-image` 变了且当前在出图，就从出图 prompt/image_preflight/image gate 起；只有 `n2d-review`/`n2d-dashboard` 变了，一般先重跑 gate/审查，不重抽图。对 owner 跨多阶段的 skill（如 `n2d-script`），按变动文件映射到具体阶段——只改分镜侧文件（`finalize_storyboard.py` 等）从 `script_stage2` 起，不回到拆集改编。测试文件（`test_*.py`/`tests/`/`conftest.py`）不计入指纹。
- **保留旧产物**：真正重制前，执行者应把将被替换的图/视频/计划移入 `废料/` 或按 stage skill 既有归档规则处理，不能直接覆盖无痕。
- **共享定妆库默认沿用（出图两层复用铁律）**：出图是两层架构——**共享定妆库**（`出图/共享/图片/` 的定妆照/场景照 PNG + `identity_registry.json`，全篇/跨集复用的锁定档案）与**本集分镜帧**（一镜一图）。当重制范围覆盖 `image` 时，**共享定妆库默认沿用、不重出**，重制范围只覆盖本集分镜帧——计划会写出 `shared_lock_reuse=true` 并把队列 scope 标成"复用共享定妆库·只重出本集分镜帧"（n2d-image 的「共享先行硬闸门」本就会跳过已 ✅ 的共享 PNG、直接以其为参考重出分镜）。**例外**：本次变更命中定妆库生产规则清单（标准三视图/角色一致性 checklist/资产身份注册层/资产引用注册层/LoRA 一致性/平台主体能力），或改到 `n2d-image/SKILL.md` 与未知 `references/` 规则文件时，`shared_lock_reuse=false`、计划标"共享定妆库需复核"；须先按最新规则复核、必要时重出共享定妆/场景，再用 `python3 skills/n2d-image/scripts/asset_impact.py <作品根> <改动的定妆资产>` 级联出引用它、需跟着重出的本集分镜。这条治"skill 一更新就把定妆照/场景照也全部重抽"的浪费，同时避免未知规则更新后错误沿用旧定妆。
- **重出图必带像素验证步**：重制范围覆盖 `image` 阶段（会重出 PNG）时，计划的建议命令会**自动追加** `dashboard gate --stage image` 作为验证步——该 gate 现已合并出图落档机检 `image_qc`（崩脸/服装/场景/接缝/lint + `CHAR_xx` 合法性），所以"重出图 → 验像素一致性"闭环自动接上，不会出现"重出了图却没人验"。`image` 已过的范围（如只重制 video→compose）不追加。`image_qc` 的硬阻断让 gate 非零，初筛项 warn 交人判。

## 重制策略（选择点 `更新重制策略`）

`build_plan` / `check` 按选择点 `更新重制策略` 决定重制力度，解析顺序走 `skills/n2d/references/选择点与偏好.md`：CLI `--regen-mode` > `<作品根>/_设置.md 更新重制策略` > 私有全局默认 > 默认 `最小`。需要修改或审计项目设置时走 `n2d-settings`。

- **`最小`（默认·保守）**：现有行为——只回放到该集已到阶段、按变动文件算最小重制范围，不默认整集重出。
- **`严审刷新`（推荐·按最新预期严审旧图）**：本模式不是“尽量保住图片”。当重制范围覆盖 `image` 时，先刷新到最新分镜 / 出图 prompt，再用最新 prompt、gate、QC、review 标准审现有图片；只要旧图不符合最新预期，就舍弃并排入重出。旧名 `保图刷新` 仅作为兼容 alias，读到后也归一为 `严审刷新`。
  1. `n2d-batch queue.py plan --rerun-from <文字阶段>` —— 按最新 skill 刷新文字阶段与出图 prompt，封顶到 `image_prompt`，让最新 prompt 成为审旧图标准；
  2. `image_qc.py --regen-list --strict` —— 对现有图片按最新 prompt/QC 标准严审，block / warn / 降级都先进入候选重出清单；
  3. `shots=$(image_qc.py --affected-shots --strict); [ -n "$shots" ] && queue.py plan --rerun-from image $shots` —— 只把有证据不符合最新标准的镜排进重生成；没有证据才不排；
  4. `dashboard gate --stage image` —— 重出的镜回验像素一致性。
  - **判定线**：旧图不是默认可用。`image_qc --strict` 会把 prompt lint、身份/服装/场景/接缝/锚点门的 block/warn/降级命中都列为候选重出；只有已有 gate/QC/review finding 或显式人工判定确认“符合最新 prompt，且不影响连续性/叙事/画风”，才允许保留旧图。
  - **执行边界**：本 skill 仍只生成计划和建议命令，不直接删图、不直接烧图。执行方重出前要按既有归档规则把被替换图片移入 `废料/` 或 stage skill 的归档位置。

## `media` 子命令 — 少量图片/视频选择性刷新

只想重出某集里几张图 / 几个 Clip，而不是整集全链重跑时，用 `media`：

```bash
python3 skills/n2d-update/scripts/update_plan.py media <作品根> 第3集 --image Clip_001,Clip_002 --video Clip_004 --write-plan
```

- `media` 必须指向具体作品根，并要传集号（位置参数或不传则按"全集"，但 n2d 要求集号，避免误扫全剧）；`--image` / `--video` / `--target` 都可逗号分隔多个目标；未列入 targets 的图片/视频默认不动。
- `--write-plan` 写 `生产数据/media_refresh_plan_第N集.{json,md}`，并追加 `生产数据/skill_update_runs.jsonl`，方便回看每次刷新计划做了什么。
- 计划 JSON 的 `execution_steps[]` 按顺序区分 `type=command`（可执行 shell）与 `type=agent_step`（需要 AI 代理按对应 SKILL 路由），`commands[]` 只保留可执行命令。

**media 原则（证据驱动，不审片）：**

- **只生成计划**：`media` 是选择性刷新计划生成器，不替代 `n2d-review` 或各 gate/QC 做审片。
- **判定来源**：所有"坏/能用/可沿用/需重制"的结论，必须来自已有 gate/QC/review findings（含 severity、affected shots/artifacts、return_to_stage 等）或显式人工输入。
- **无证据不判**：没有 findings 或人工判定时，`media` 只能列出下一步复核命令/人工确认步骤；不得把 `--image`/`--video`/`--target` 直接当作坏目标，也不得无条件排入重制。
- **不碰未列目标**：`media` 是少量图片/视频刷新工具，不做整集全链重跑。

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
- `newly_relevant_skills`：阶段推进后首次纳入相关范围的 skill，不计为变更（无旧基线可比）；该阶段完成后 `record` 刷新基线，使其纳入内容快照。
- `current_stage`：用于更新上界的当前阶段；若前序有缺口但后续已有产物，取已开始的最远阶段。
- `current_todo`：当前生产缺口/下一步，来自 `_进度.md` 的首个未完成阶段；它和 `current_stage` 可以不同。例如 `current_stage=video` 表示 update 影响上界，`current_todo=image` 表示当前还应先补图。
- `rerun_from`：建议回放起点。
- `rerun_until`：最多重制到的阶段，永远不超过该集当前进度。
- `shared_lock_reuse`：重制覆盖 `image` 且**未**命中定妆库生产规则时为 `true`——共享定妆库（定妆照/场景照）默认沿用、不重出，重制只覆盖本集分镜帧。
- `shared_lock_changed_files`：命中定妆库生产规则的变动文件；非空表示共享定妆库需复核（`shared_lock_reuse=false`）。
- `source_drift`：源小说漂移检测（`source_check.py` 的 DRIFT；`status` clean/drift/no_baseline）。无 `小说/_源指纹.json` 基线时为 `null`。
- `three_frame_compliance`：三帧契约遵循（`enforced` 按后端能力门控、`violating_clips` 缺中段锚帧的 Clip、`compliant`）。storyboard 未定稿为 `null`。
- `image_consistency`：图片一致性摘要（`hard_blocks`/`verdict`/`consistent`），来自 image_qc 报告；未到出图阶段为 `null`。
- `contract_inheritance`：出图→出视频契约继承摘要（`verdict`/`field_blocks`/`identity_blocks`/`asset_blocks`/`inherited`，`status` ok/missing/error），来自 `inherit_contract.py` 报告；未到 `video_prompt` 阶段为 `null`，已到但报告缺失为 `status=missing`（提示先跑 inherit_contract 取证）。
- `execution_steps`：建议执行步骤；区分可执行命令、AI/人条件判断、以及重出完成后的验收命令。
- `commands`：兼容旧调用方的命令字符串列表；新调用方应以 `execution_steps` 的 `type/run_when` 为准。
- `smart_suggestions`：从 dashboard 生产事件中提取的角色/后端升档建议；`--json` 模式写进 JSON，不污染 stdout。

无基线时，`check` 会给出 `needs_record=true`，并提示先 `record` 建立内容快照基线；在建立基线之前无法检测变更（不依赖 git 工作区兜底）。读到旧版 git 派生基线（无内容表）时同样提示重新 `record`。

## 常见错误

| 错误 | 纠正 |
|---|---|
| 不等用户确认直接开跑重制 | 本 skill 仅提供最小范围的“重制计划”。实际运行必须先跟用户沟通，再交由 `n2d-batch` 执行 |
| 把更新提醒当成生产故障 | `rebuild_needed=true` 只是提示 skill 有新逻辑升级，并不意味着旧产物已经坏掉 |
| 重制前没有先清理原产物 | 要提醒执行方先移除或归档将被替换的“废料”，以防发生重叠或残留 |
