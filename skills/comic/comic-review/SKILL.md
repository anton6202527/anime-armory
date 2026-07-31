---
name: comic-review
description: 画漫画审查阶段。Use when reviewing comic scripts, name boards, layouts, traditional ink/tone/effects coverage, panel art, lettering, bilingual lettering, empty bubbles, long-scroll exports, readability, panel order, text overlap, hand/foot anatomy, character consistency, source adaptation faithfulness, platform deliverable readiness, or rework lists for projects under 创作区/画漫画. Triggers 漫画审查, 漫画质检, 阅读顺序, 遮挡, 角色一致性, 手脚错乱, 空气泡, 双语嵌字, 台词太多, 长图检查, 缩略分镜检查, name board review, 网点检查, 效果线检查, 发布前检查, comic-review.
---

# comic-review — 漫画审查、阶段 Gate 与发布裁决

comic-review 负责证明“当前版本是否可以继续”，不负责代写脚本、改图或代替人签收。审查分三层：确定性合同 gate、启发式视觉/叙事告警、人工责任签收。最终再由 `release_verdict.py` 把技术完成、生产完成和公开发布就绪分开。

## 证据规则

- **可 block 的确定性事实**：缺文件、非法 schema、合同必填字段缺失、章节/source/panel 覆盖不闭合、角色 binding 或 registry 状态不可解析、真实参考缺失、审批/签收缺失、SHA stale、job 与当前合同不一致、缺 panel、post-QC 确定性失败、manifest 或渲染物缺失、目标发布 profile 的权利条件不满足。
- **只能 warn/info 的启发式信号**：节拍关键词、台词/构图重复相似度、CCIP/embedding、face/hair/outfit 色彩指纹、dHash、黑白灰/线宽代理、场景布局指纹、调色离群和多模态模型判断。即使来源报告标成 block，gate 也应按启发式置信度降级。
- **人审签收不能覆盖确定性缺件**：可签收计划内光效、遮挡、低机位、换装、蒙太奇或像素代理误报；不能批准不存在的图片、缺参考、错误 schema、失效合同或明显使用了错误人物/服装。
- **所有签收绑定当前证据**：图片、任务或上游内容变化后，旧 SHA receipt 自动失效。

## 输入

- `_设置.md`、`_meta.json`、`_进度.md`。
- 开发包、`split_blueprint.json`、本话 `source_semantics.json` 和 `panel_script.json`。
- `identity_registry.json`、model-pack report/signoff、共享参考图。
- `name_board.json`、`layout.json`、`finishing_plan.json`。
- reference plan、`panel_jobs.json`、panel PNG 与逐格 post-QC。
- `lettering.json`、`export_manifest.json` 和真实渲染物。

## 输出

- `生产数据/comic_gate_<stage>_第N话.json/md`：完整 gate 报告。
- `生产数据/gate_findings_<stage>_第N话.json`：结构化 finding。
- `生产数据/gate_receipts/<stage>_第N话.json`：绑定 stage 输入 fingerprint、报告 SHA 和 panel jobs SHA 的收据。
- `生产数据/comic_continuity_audit.json/md`：跨话 entry/delta/exit 确定性审计。
- `生产数据/comic_style_consistency_第N话.json/md`、`comic_character_consistency_第N话.json/md`、`comic_scene_prop_consistency_第N话.json/md`：视觉一致性证据与返修目标。
- `生产数据/comic_vlm_judge_tasks_第N话.json` / `comic_vlm_judge_verdicts_第N话.json`：**CANVAS 四轴**并排判定任务与裁决——① `character_identity` 角色/生物脸·服装·体型（含 `MON_/BEAST_/ANIMAL_`，防「虎妖画成普通虎、狐妖画成狗」）、② `location_identity` 场景身份（本格背景 vs 该 `LOC_` 自己的定妆锚，防画错场景/换成别处）、③ `background_continuity` 同场景锚相邻格布局/光位、④ `prop_identity` 道具/武器身份位置（含 `WEAPON_`，防「断横刀换成弯刀」）。执行闭环用 `vlm_adjudicate.py <作品根> --chapter 第N话 queue [--batch-size N --axis <轴>]` 出队待裁决任务（含绝对路径），由多模态 agent 看图打分后把 `{"verdicts": [...]}` 文件交给 `submit` 子命令——逐条校验 panel/task/reference SHA 与 evaluator 后合并回写，任何一条非法整批拒绝。image gate 核对**分轴**裁决覆盖率：任务包存在但 0 裁决 → `vlm_judge_unadjudicated`（机检空转，第1话 P015 虎妖漏放实证）；**角色一致性硬闸=开启时，凡 `location_identity/background_continuity/prop_identity`（CCIP 覆盖不到、无判定引擎兜底的轴）存在任务且 0 裁决即升 `block`——无论 CCIP 装没装**（CCIP 只覆盖角色身份 embedding，覆盖不到场景/背景/道具/生物形态）；仅角色轴 0 裁决且 CCIP 不可用亦 block；某无兜底轴整轴漏裁决而其它轴已裁 → `vlm_judge_axis_blind` block；部分裁决 → `vlm_judge_partial_coverage` warn；CCIP 不可用 → `identity_similarity_engine_degraded` warn。
- **CCIP 外部解释器桥**（`ccip_bridge.py`）：gate/review 跑在装不了 dghs-imgutils 的解释器时，自动路由到 `COMIC_CCIP_PYTHON` 指定解释器或约定 conda env `comicqc`（`conda create -n comicqc python=3.11` + `pip install dghs-imgutils onnxruntime`），常驻 worker 批量算 CCIP 距离（模型仅加载一次）。桥不可用才降级色彩代理；`comic` doctor 会报告当前模式（inprocess/external_worker/unavailable）。
- `生产数据/qa_previews/`：panel、角色、风格 contact sheet 和长图预览。
- `生产数据/comic_review_第N话.json/md`：综合审查报告。
- `生产数据/release_verdict_第N话.json/md`：技术/生产/发布状态裁决。

## 阶段 Gate

正式链路按阶段运行；后一个 stage 会复核其依赖的前置合同：

```bash
ROOT="创作区/画漫画/作品名"
python3 skills/comic/comic-review/scripts/gate.py "$ROOT" --chapter 第1话 --stage script
python3 skills/comic/comic-review/scripts/gate.py "$ROOT" --chapter 第1话 --stage name
python3 skills/comic/comic-review/scripts/gate.py "$ROOT" --chapter 第1话 --stage layout
python3 skills/comic/comic-review/scripts/gate.py "$ROOT" --chapter 第1话 --stage finishing
python3 skills/comic/comic-review/scripts/gate.py "$ROOT" --chapter 第1话 --stage image_preflight
python3 skills/comic/comic-review/scripts/gate.py "$ROOT" --chapter 第1话 --stage image
python3 skills/comic/comic-review/scripts/gate.py "$ROOT" --chapter 第1话 --stage compose
python3 skills/comic/comic-review/scripts/gate.py "$ROOT" --chapter 第1话 --stage review
```

| stage | 确定性验收重点 | 告警/人审重点 |
|---|---|---|
| `script` | 生产档位自洽；开发包 strict 通过且 signoff SHA 当前；source trace/合同绑定；visual contract 和跨话状态无矛盾 | 节拍、钩子、软容量、冗余仅提示 |
| `name` | script 通过；name schema v2、`approved`、审批主体和上游 SHA 当前 | 页流、翻页钩子、格子轻重、气泡优先级 |
| `layout` | name 通过；layout schema v2、validator、几何 profile、approval SHA 当前 | 破格/跨页/特殊装帧的人工节奏 |
| `finishing` | 已签收 name/layout；逐格/逐页同序覆盖；上游 SHA 当前 | 黑场、网点、效果线、拟声词的审美作用 |
| `image_preflight` | registry v2；结构化 bindings；model pack 技术齐套且当前人审签收；reference plan/job 当前；真实引用闭合；后端/profile/compiler 一致 | 节拍、话内冗余、追更再入前情、去 AI 味直白率、构图重复和像素代理只 warn |
| `image` | preflight 通过；必需 panel 文件存在；job `ready`；生成合同 SHA 当前；确定性 post-QC 无 block | 风格/角色/场景/道具/画面相似度告警需看原图 |
| `compose` | image 通过；lettering/manifest 存在；无 missing panels；有真实渲染物；平台 profile 可验证 | 文字密度、留白与疑似气泡需逐页人审 |
| `review` | compose 通过；综合报告无确定性 block | 阅读、表演、审美、改编效果和告警处置 |

gate 即使 block 也会写 receipt，因此“文件存在”不等于通过。消费者必须同时检查：`verdict != block` 且 `inputs_fingerprint_sha256` 与当前 stage 输入一致。任一输入变化后重跑相应 stage，不复制旧收据。

`--no-refresh` 只禁止刷新 identity report；不会把旧 style/character 结果当成永久事实。

## Script 与连续性审查

正式 script gate 会运行开发包 strict 检查，并把以下事实作为硬合同：

- 每话 chapter contract 有明确 source mode、读者承诺、冲突、转折、兑现、ending mode 和软 budget。
- 改编项目的 source spans 文件存在，未说明缺口/重叠被阻断；`source_semantics.json` 绑定当前合同/源 SHA，逐格 source refs 覆盖有效。
- `panel_script.json.chapter_contract_sha256` 绑定 `split_blueprint.json` 中当前本话合同。
- 长线合同 `entry_state → continuity_delta[] → exit_state` 可计算；每个 transition 有 `entity_id/field/from/to/panel_id/reason`，证据格存在；上一话 exit 与下一话 entry 不矛盾。
- `visual_contract.scene_anchors`、角色完整性、具体 gaze target、空间布局、光位/冷暖和轴线可执行。

单独运行跨话审计：

```bash
python3 skills/comic/comic-review/scripts/continuity_audit.py "$ROOT" --through-chapter 第1话 --write --strict
```

## 身份、多视图和逐格引用审查

`image_preflight` 不把“有一张角色图”当长期一致性完成。它会复核：

- `identity_registry.json` 为 schema v2；角色 form/outfit/expression/state/default binding 合法。
- 每个具名角色都有本格 `character_bindings[]`；未知或互相冲突的 ID 直接阻断 job。
- 角色按 `library_tier` 补齐必需视图，确定性技术检查没有重复图冒充、错误视图、占位图或比例基线问题。
- 核心多视图有当前 SHA 的人工并排签收；任一视图变化后 signoff stale。
- LOC、常驻 PROP、服装和关键 VFX/STYLE 引用已登记且有真实图片。
- reference plan 先保证每个具名角色至少一张身份锚，再保留场景/道具；超过后端附件上限时明确拆格或分区合成。
- panel jobs 实际消费 reference plan，记录选中图片 SHA、`panel_plan_sha256`、`execution_input_sha256` 和 `consumed_contracts`。

多视图技术检查和签收由 `comic-identity` 执行；comic-review 只验证其结果是否当前有效。

## 视觉一致性与启发式告警

可分别运行：

```bash
python3 skills/comic/comic-review/scripts/style_consistency.py "$ROOT" --chapter 第1话
python3 skills/comic/comic-review/scripts/character_consistency.py "$ROOT" --chapter 第1话
python3 skills/comic/comic-review/scripts/scene_prop_consistency.py "$ROOT" --chapter 第1话
```

- 风格报告检查生成配方、风格锚、场景族群、相邻格冷暖/亮度、黑白灰/线宽代理、拼贴 gutter/外框嫌疑和跨话 baseline。文件缺失与配方矛盾可确定性处理；像素离群只告警。
- 角色报告把每个 CHAR/MON 参考与出场 panel 并排，CCIP 可用时做动漫身份 embedding 快筛，Pillow 指纹做辅助。公开 fallback 和项目内自标定都只驱动 warn，不给“相似度分数”硬阻断权。
- 场景/道具报告按 LOC/PROP/VFX/OUTFIT 生成 contact sheet 和布局指纹；引用缺失是确定性问题，布局/色彩偏离是人审线索。
- 多模态裁决只有在 panel SHA、task SHA、全部 reference SHA 和 evaluator `model/version` 与当前任务完全一致时才有效；重抽或换参考后旧 verdict 自动忽略。

如果有人工金标集，可生成项目阈值登记：

```bash
python3 skills/comic/comic-review/scripts/calibrate_thresholds.py "$ROOT" --write --json
```

只有达到脚本规定的正/负样本数量和 balanced accuracy 才标为 validated；登记仍是 `warn_only`。样本或 gold set SHA 变化后旧校准失效。

## 人审告警签收

三类兼容签收文件：

- `生产数据/style_consistency_acceptance_第N话.json`
- `生产数据/character_consistency_acceptance_第N话.json`
- `生产数据/raw_bubble_acceptance_第N话.json`

每个 accepted finding 至少写 `code`、`panel_id` 或 artifact、`reason`、`evidence`，并应写当前 `artifact_sha256`；角色告警可再写 `character_id`。带 SHA 的签收在重抽后自动失效。不带 SHA 的旧签收只作兼容记录，应补齐证据。

`panel_qc.manual_review.verdict=pass` 只覆盖该格 post-QC 的启发式 warn；不能改变文件损坏、缺参考或合同 stale。

## 综合审查与进度

生成报告默认不回写进度：

```bash
python3 skills/comic/comic-review/scripts/review.py "$ROOT" --chapter 第1话
```

只有报告 `verdict=pass` 且用户明确要求，才允许：

```bash
python3 skills/comic/comic-review/scripts/review.py "$ROOT" --chapter 第1话 --write-progress
```

审查至少覆盖阅读顺序、叙事闭环、气泡/文字遮挡、角色和服装、人物完整性、眼神、场景/轴线、手脚与道具接触、传统工艺层、语言、导出规格和权利可追溯。详细项见 `references/review_checklist.md`。

每个 finding 必须有：

- `severity`：block / warn / info。
- `artifact`：文件或 panel ID。
- `reason`：对生产或交付的具体影响。
- `return_to_stage`：返回哪个裸 skill。
- `suggested_fix`：最小返修动作。
- `evidence_family/confidence`：证明它是确定性事实还是启发式线索。

## 生产完成与发布裁决

综合 review 通过不等于自动可公开发布。运行：

```bash
python3 skills/comic/scripts/release_verdict.py "$ROOT" 第1话 --profile internal --write --json
python3 skills/comic/scripts/release_verdict.py "$ROOT" 第1话 --profile digital \
  --accept --reviewer "责任编辑" --reason "最终导出物与审查证据复核通过" --write --json
python3 skills/comic/scripts/release_verdict.py "$ROOT" 第1话 --profile digital --write --json
python3 skills/comic/scripts/release_verdict.py "$ROOT" 第1话 --profile print --write --json
python3 skills/comic/scripts/release_verdict.py "$ROOT" 第1话 --profile commercial --write --json
```

裁决含：

- `technical_complete`：manifest 和当前真实渲染物完整。
- `production_complete`：technical complete，且当前 review gate receipt 非 block。
- `publish_ready_internal/digital/print/commercial`：按 profile 追加权利与最终人审签收。

`digital/print/commercial` 必须由真实签收人显式执行 `--accept --reviewer ... --reason ...`。命令先排除 acceptance 自身之外的发布阻断，再写 `生产数据/release_acceptance_第N话.json`；其 `status/reviewer/approved_at` 有效，`artifacts[]` 与当前全部导出物 `path/sha256` 完全一致，`review_receipt` 也精确绑定当前 review gate receipt。它只记录明确的人审决定，不自动决定、不发布、不回写进度。

## 不做什么

- 不直接重写脚本、替换 layout、重抽 panel 或修改最终成品。
- 不用“好看/不好看”或未校准分数作硬阻断。
- 不把草稿字体、素材 pending 或内部 review 冒充公开发布授权。
- 不因 receipt 文件存在就忽略 verdict 与 SHA freshness。
