---
name: n2d-update
description: 制漫剧(n2d) skill 更新影响扫描与重制计划器（含少量图片/视频选择性刷新 `media` 子命令）。Use when the user says 更新/重制/update/rebuild/refresh 某个 n2d 作品或某集，asks whether updated n2d skills require rerunning work, or wants to 只重出部分图片/部分视频. It reads `_进度.md`, detects relevant `skills/` changes against a stored snapshot, plans the minimum safe rerun only up to the episode's reached production stage, writes `生产数据/skill_update_plan_第N集.{json,md}`, and tells the user what to re-run before any paid generation; the `media` 子命令为指定集/指定 Clip 生成证据驱动的选择性刷新计划。Triggers 更新, update, 检查更新, skill升级, 重制计划, 媒体重制, 部分图片重制, 部分视频重制, 只重出部分图片, 只重出部分视频, n2d-update.
---

# n2d-update — skill 更新影响扫描 + 最小重制计划 + 选择性媒体刷新

> **本 skill 是制漫剧线唯一的更新/重制入口（n2d 专用）。** 原跨线 `update` 分发器已于 2026-06 退场——其他创作线暂不需要更新嗅探，媒体选择性刷新作为本 skill 的 `media` 子命令并入。

这是制漫剧线的**更新/重制调度 skill**。它不直接调用生图、生视频、配音或合成后端；它先做确定性分析：

1. 读 `<作品根>/_进度.md` 判断指定集已经走到哪一步。
   - 若前序列仍有小缺口（如 `字幕英` 未补）但后续阶段已经开始（如 `出图 25/35`），更新上界按**已开始的最远阶段**算，避免漏掉已有产物受新 gate/review 逻辑影响的范围。
2. 取到当前阶段为止相关 n2d skills 的基线。基线是 **文件内容快照**：相关 skill 文件逐个内容 SHA256 表（`files`），**不依赖 git 或任何版本控制**——交付到用户端零 VCS 依赖，中文路径也天然无障碍；`n2d-lora` 这类横切身份锁生产规则也纳入基线，避免 LoRA 生命周期策略变更在花钱前不可见。
3. 重算当前 `skills/` 相关文件内容 SHA 并与基线 `files` 表逐项比对，hash 不同即变更，找出改过的 skill。（旧版 git 派生基线只有 `git_commit`、无内容表，读到时提示用户重新 `record` 建立内容基线。）
4. 生成“从哪一阶段回放、最多重制到哪一阶段、哪些产物需要 diff/复核”的计划。
   - 同时单独写出**当前生产缺口**：即便更新影响上界因已有视频产物算到 `video`，也要从 `_进度.md` 首个未完成项补出“当下该做什么”（如 `出图 69/85 → n2d-image`），避免 update 计划把真实生产前沿藏掉。
5. 付费/不可逆步骤只给计划和队列建议，必须等用户确认后再交给对应 stage skill 或 `n2d-batch`。

除了 skill 变更，`check` 还跑**四项产物健康检测**（写进计划 `source_drift`/`three_frame_compliance`/`image_consistency`/`contract_inheritance`，CLI 打 `health:` 行）：

- **源小说漂移**：跑 `n2d/source_check.py`（有 `小说/_源指纹.json` 基线才跑），本剧源文本一改即发现源过期 → 列变动章 + 落在哪些集。重切属不可逆点，只提示不自动切。
- **三帧契约遵循**：读 `脚本/第N集/storyboard.json`，按 `policy.video_backend` 的后端能力判定（能力门控铁律：支持≥3帧的后端强制），列出缺 `midframe/anchors` 且无豁免理由的违规 Clip；同时核验已声明的中段锚帧/尾帧 PNG 是否实际存在（兼容 `clip.endframe_png` 旧字段，但仍要求文件落档）→ 指回 `anchor_planner.py --write` 补齐声明，再回 n2d-image 出 `_mid/_aK/_end` 帧。后端不支持≥3帧（first-frame-only）则标豁免、不算违规。
- **图片一致性**：从已有 `image_qc` 报告压出崩脸/服装/场景/接缝硬阻断摘要（`hard_blocks`/verdict），有硬阻断则提示重出受影响镜。
- **出图→出视频契约继承**：到 `video_prompt` 阶段后，读 `n2d-video/inherit_contract.py` 的产物 `生产数据/contract_inheritance_第N集.json`，压出 verdict + 字段漂移/身份未锁/资产丢失计数——校验**参考帧契约**（色调/光位锚/轴线视线/角色状态演进/景别）与**文字 prompt** 是否从出图侧正确传到出视频侧、命名角色镜是否锁脸、出图绑定的场景/道具/特效资产是否丢失。本 skill 只读报告不自己跑机检（出视频前的契约门由 n2d-video 把）：已到 `video_prompt` 但**缺报告** → 提示先跑 `inherit_contract.py <作品根> 第N集` 取证；verdict=`block` → 提示先按出图侧原文修 `出视频/prompt` 的视觉契约/身份锚点/物料绑定再出视频。

**报告新鲜度（不信过期结论）**：image_qc 与 inherit_contract 报告都盖了 `inputs_fingerprint`（其判定所依据的 PNG/prompt/registry 文件内容快照，git-free SHA256）。`check` 重算同一组文件的指纹与报告里的比对，给出 `freshness`：`fresh`（输入未变）/ `stale`（报告生成后出图或 prompt 又被重生成，结论作废）/ `unknown`（旧版报告无指纹）。`stale`/`unknown` 时计划提示**先重跑对应 gate/机检再据此判断**，避免拿一份描述旧产物的报告当现状。

## 输入 / 输出 / 读写边界

- **输入**：`_进度.md`、当前 `skills/` 相关文件内容、上次记录的 skill snapshot（内容 SHA 快照）、指定集当前前沿。**不读 git 状态。**
- **输出**：`生产数据/skill_update_plan_第N集.json/md` 和 skill snapshot 记录（相关 skill 文件的内容 SHA 表，无版本控制依赖）。
- **读写边界**：只写更新影响计划和基线；不删除旧产物、不重跑阶段、不改 `_进度.md`。
- **契约关系**：阶段顺序、当前前沿和最多重制范围来自 `skills/n2d/_lib/n2d_contract.py`，避免把 stage 映射写散。变动文件→阶段的映射表（`N2D_LIB_FILE_STAGE_HINTS` / `…_OBSERVE_ONLY_TOKENS` / `SKILL_FILE_STAGE_HINTS` / `N2D_IMAGE_SHARED_LOCK_RULE_FILES`）由 `scripts/test_hint_coverage.py` 守护：新增 `_lib` 模块未分类、或被引用的文件被重命名导致 token 落空时测试即失败，防止"映射漂移→静默回退到 script_stage1 全链重制"的烧钱隐患。

## 快速使用

```bash
python3 skills/n2d-update/scripts/update_plan.py check <作品根> 第1集 --write-plan
python3 skills/n2d-update/scripts/update_plan.py record <作品根> 第1集
python3 skills/n2d-update/scripts/update_plan.py check <作品根> --all --write-plan
# 少量图片/视频选择性刷新（证据驱动，不审片）：
python3 skills/n2d-update/scripts/update_plan.py media <作品根> 第1集 --image Clip_001 --video Clip_002 --write-plan
```

- `record`：在一次阶段完成、用户接受现状、或完成重制后，记录当前 skill 基线（相关 skill 文件的内容 SHA 快照）。**推荐把它当成每个阶段的收尾步**（产完一阶段物料、验收通过即 record），这样基线始终贴着"这批产物是哪个 skill 版本出的"，而不是事后补记。
  - 作品级快照不会因只记录某一集的较早阶段而缩窄历史范围；已纳入过的 skill 会保留，避免第2集 record 覆盖掉第1集视频阶段的基线。
  - 基线即"record 当刻的文件内容"；记录后这些内容就是新基准，下次 `check` 只报相对它的真实改动。
- `check`：对比基线；若相关 skill 变了，输出是否建议重制。
  - **无基线自愈（bootstrap）**：若该作品还没有基线，`check` 会**自动建立一份临时基线**（`baseline_bootstrapped=true`）而不再死胡同在 `needs_record`——从这一刻起就能检测变更。临时基线看不到"此前已用过的更早 skill 版本"所致的差异；确认当前产物可接受后请 `record` 固化为正式基线（清除临时标记）。要保留旧的"无基线就罢工"行为，加 `--no-bootstrap`。
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
- **预读已有证据**：磁盘上已有 `image_qc` / `contract_inheritance` 报告时，`media` 会**逐 target 预读**这些 findings，按 clip 号/png 名匹配，标出每个 target 的 `evidence_verdict`（`block`/`warn`/`no_evidence`）写进计划的 `evidence` 段——命中 block 的可在人工确认后直接排重出，无命中的留待复核。报告齐全时 `needs_decision_evidence=false`，不再把取证整段甩回操作者。
- **无证据不判**：没有 findings 或人工判定时（无报告即 `evidence_verdict=no_evidence`），`media` 只能列出下一步复核命令/人工确认步骤；不得把 `--image`/`--video`/`--target` 直接当作坏目标，也不得无条件排入重制。
- **不碰未列目标**：`media` 是少量图片/视频刷新工具，不做整集全链重跑。

## 出图/出视频前的自动哨兵（gate 侧「物料新鲜度」预检）

同一套 skill 漂移检测已下沉到 `n2d/_lib/skill_freshness.py`，被 `n2d-review` 的
`image_prompt_preflight` / `image_preflight` / `video_prompt_preflight` / `video_preflight`
预检在**正式调用后端花钱前**自动跑一次：若生产本阶段输入物料的 skill（n2d-script/voice/image/video
或 `n2d/_lib` 运行期契约）自上次 `record` 的基线后有改动，预检会发一条 **WARN「物料新鲜度」**——
*前期物料可能已过期，先跑 `update_plan.py check` 评估哪些物料需重制再生成*。这是 **advisory·不硬阻断**
（是否重制是判断题，交给本 skill 的精确规划器；横切/QC/gate-only 改动只发 INFO 不报过期），WARN 与
BLOCK 区分见 `add()` 严重度模型。

**前提**：哨兵只在作品**已有基线**时说话——无基线 = 无可比对对象，预检**静默**。要开启它，先在产完一个
阶段、验收通过时跑一次 `record`（见下「`record`」），此后每次出图/出视频前都会自动体检 skill 漂移。
gate 侧只读不写、永不自动落基线；精确的「文件→阶段 / artifact vs gate-only」裁决仍由本 skill 的
`check` 给出。

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
- `three_frame_compliance`：三帧契约遵循（`enforced` 按后端能力门控、`violating_clips` 缺中段锚帧声明的 Clip、`missing_endframe_clips` 缺尾帧声明的 Clip、`missing_frame_files` 已声明但 PNG 不存在的帧、`compliant`）。storyboard 未定稿为 `null`。
- `image_consistency`：图片一致性摘要（`hard_blocks`/`verdict`/`consistent`/`freshness`），来自 image_qc 报告；未到出图阶段为 `null`。`freshness=stale` 表示报告已被后续出图重生成作废。
- `contract_inheritance`：出图→出视频契约继承摘要（`verdict`/`field_blocks`/`identity_blocks`/`asset_blocks`/`inherited`/`freshness`，`status` ok/missing/error），来自 `inherit_contract.py` 报告；未到 `video_prompt` 阶段为 `null`，已到但报告缺失为 `status=missing`（提示先跑 inherit_contract 取证）。
- `freshness`（上两项内）：`fresh`/`stale`/`unknown` —— 报告的 `inputs_fingerprint` 与当前输入文件内容比对结果；`stale`/`unknown` 提示先重跑机检再信结论。
- `baseline_bootstrapped`：基线是否为 `check` 自动建立的临时基线（bootstrap）。`true` 时计划照常输出，但提示此前更早 skill 版本的差异不可见，建议接受现状后 `record` 固化。
- `execution_steps`：建议执行步骤；区分可执行命令、AI/人条件判断、以及重出完成后的验收命令。
- `commands`：兼容旧调用方的命令字符串列表；新调用方应以 `execution_steps` 的 `type/run_when` 为准。
- `smart_suggestions`：从 dashboard 生产事件中提取的角色/后端升档建议；`--json` 模式写进 JSON，不污染 stdout。

无基线时，`check` 默认**自动建立临时基线**（`baseline_bootstrapped=true`）让检测自愈，并提示确认现状后 `record` 固化；加 `--no-bootstrap` 则保留旧行为：给出 `needs_record=true`、在建立基线前不检测变更（不依赖 git 工作区兜底）。读到旧版 git 派生基线（无内容表）时同样提示重新 `record`。

## 完成后 · 详列下一步（收尾必做 · 只提示不自动跑）

`check`/`media` 跑完后，**把计划念给用户**——重制要花钱/覆盖产物，必须等用户确认再交 `n2d-batch` 或对应 stage skill 执行（见 `n2d` SKILL 情境 D）：

```
第K集 skill 更新影响检查完成：
- 变更 skill：<changed_skills>（无变化则报"无更新，静默继续"；无基线则提示先 record）
- 当前阶段上界 current_stage=<…>；当前缺口 current_todo=<…>
- 计划：从 <rerun_from> 回放，最多重制到 <rerun_until>（永不超过该集当前进度）
- 共享定妆库：<沿用不重出 / 需复核>；源漂移：<clean/drift/no_baseline>
下一步建议（按 execution_steps 念给用户，逐条标"可执行命令 / 需人确认 / 验收命令"）：
- 确认重制范围后：python3 skills/n2d-batch/scripts/queue.py plan <作品根> --episodes K --rerun-from <stage> [--affected-shot …]
- 或直接回跑对应 stage skill（n2d-image / n2d-video / …）从 <rerun_from> 起
- 重制结束后记录新基线：python3 skills/n2d-update/scripts/update_plan.py record <作品根> 第K集
- 整部进度总览：n2d-progress <作品根>
```

> 无变化时也要明确告诉用户"本集 skill 无更新，按原前沿继续"，并给出 `n2d-progress` / `progress.py` 的下一步，别让用户卡在不确定。

## 常见错误

| 错误 | 纠正 |
|---|---|
| 不等用户确认直接开跑重制 | 本 skill 仅提供最小范围的“重制计划”。实际运行必须先跟用户沟通，再交由 `n2d-batch` 执行 |
| 把更新提醒当成生产故障 | `rebuild_needed=true` 只是提示 skill 有新逻辑升级，并不意味着旧产物已经坏掉 |
| 重制前没有先清理原产物 | 要提醒执行方先移除或归档将被替换的“废料”，以防发生重叠或残留 |
