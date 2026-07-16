---
name: comic
description: 画漫画生产线总调度。Use when the user wants to create a comic, manga, manhua, webtoon, long-scroll comic, panel script, comic name board, page layout, traditional ink/tone/effects finishing, comic art prompts, character consistency, shared references, lettering, export, batch panel generation, rerolling panels, update/rebuild planning, or adapt a source story or idea into comics. It initializes or inspects projects under 创作区/画漫画, reads _进度.md, and routes to comic-script, comic-name, comic-layout, comic-finishing, comic-identity, comic-image, comic-batch, comic-compose, comic-review, comic-update, or comic-progress. Triggers 画漫画, 漫画, 条漫, 页漫, 分格, 分镜, 故事板, 缩略分镜, name board, 原稿收尾, 网点, 效果线, panel, storyboard, 定妆, 脸漂, 角色一致性, 嵌字, 气泡, 长图, 漫画出图, 漫画批跑, 重抽漫画格, 漫画更新, comic-update, comic.
---
> 规模统计：Skill 数 13 | SKILL.md 总行数 1424 | 目录文本总行数 39252

# comic — 画漫画生产线总调度

把故事源、点子或已有脚本推进为可审计的漫画成品。正式闭环不是“图片生成完”，而是：生产合同当前有效、编辑签收有效、逐格引用闭合、阶段 gate 无确定性阻断、导出物可复核；公开发布再单独完成权利和最终成品 SHA 签收。

comic 负责定位作品根、先读 `_进度.md` / `_设置.md`、解释当前前沿并路由；创作和生产动作仍由 `comic-script`、`comic-name`、`comic-layout`、`comic-finishing`、`comic-identity`、`comic-image`、`comic-batch`、`comic-compose`、`comic-review` 执行。

详细依赖和失效传播见 `references/architecture.md`；选择点见 `references/选择点与偏好.md`。

## 必走生产顺序

下面是正式章节的可执行主路径。旧项目可逐步补齐，但不能用旧产物绕过当前 gate。

### 1. 能力自检、生产档位和项目状态

```bash
python3 skills/comic/doctor.py "创作区/画漫画/作品名" --write
python3 skills/comic-settings/scripts/settings_cli.py set "创作区/画漫画/作品名" 生产档位 连载标准
python3 skills/comic-settings/scripts/settings_cli.py audit "创作区/画漫画/作品名"
```

- `doctor` 只披露本机可执行能力和项目缺件，不替代签收；缺视觉模型时可以继续做合同，但公开交付仍需当前 SHA 的人审证据。
- `生产档位` 必须通过 `comic-settings` 原子展开。正式 gate 会阻断“档位名称与联动设置互相矛盾”。
- 用户给出作品根时先读 `_进度.md`；完成态只能来自真实产物与验证，不因计划存在而写 `✅`。

新项目初始化：

```bash
python3 skills/comic/scripts/init_project.py "创作区/画漫画/作品名" --title 作品名 --mode 原创漫画
```

有源文件时追加 `--mode 源本改漫画 --source path/to/source.md`。

### 2. 开发包、章节合同和源追溯

```bash
python3 skills/comic-script/scripts/development_pack.py "创作区/画漫画/作品名" scaffold --write
python3 skills/comic-script/scripts/development_pack.py "创作区/画漫画/作品名" check --strict --json
python3 skills/comic-script/scripts/source_semantics_gate.py "创作区/画漫画/作品名" --chapter 第1话
python3 skills/comic-review/scripts/gate.py "创作区/画漫画/作品名" --chapter 第1话 --stage script
```

- 历史题材、公版名著或有多个影视版本的项目，在首张文字定妆前先落可追溯视觉研究合同：

  ```bash
  python3 skills/comic/scripts/visual_research_contract.py "创作区/画漫画/作品名" scaffold --write
  python3 skills/comic/scripts/visual_research_contract.py "创作区/画漫画/作品名" check --strict --json
  ```

  验收至少包含 1 项官方/版权方影视叙事参考、2 项博物馆/权威机构一手参考、稳定 `STYLE_...` 风格锚和有证据引用的 `derived_style`。该脚本完全离线，只记录 URL/发现/设计决策，不下载图像；所有来源均为 `research_only`，禁止影视剧照或演员肖像直接作生图锚。完整 schema 见 `references/visual_research_contract.md`。
- 填完 `开发包/adaptation_strategy.json`、`开发包/season_arc.json`、`脚本/split_blueprint.json` 后，将内容和每话合同置为 `confirmed`，再由真实 reviewer 写 `开发包/signoff.json`；签收必须含 `reviewer / role / time / file_sha256`，并精确绑定三件套当前 SHA。
- 每话合同至少声明 `source_mode / source_spans / reader_promise / core_conflict / turning_point / payoff / ending_mode / budget`。连载类话次还必须用 `entry_state → continuity_delta[] → exit_state` 记录可证据化的状态变化；`continuity_delta[]` 每项绑定实际 `panel_id`。
- 改编项目必须完成 source trace：合同源范围真实存在、无未说明缺口/重叠，`source_semantics.json` 绑定当前合同和源文件 SHA，逐格 `source_segment_refs` 能闭合覆盖。原创项目声明 `source_mode=original`，不得伪造源段。
- 划分章节按“读者承诺—冲突—转折—兑现—结尾模式”判断闭环；`budget.soft_range` 只表达产能意图，不以固定格数硬切话。

### 3. 分格脚本、结构化角色绑定与连续性

`panel_script.json` 顶层用 `chapter_contract_sha256` 绑定 `split_blueprint.json` 中本话合同，并写 `visual_contract`；每个具名角色必须逐格使用：

```json
{
  "character_id": "CHAR_A",
  "form_id": "FORM_BASE",
  "outfit_id": "OUTFIT_BASE",
  "expression_id": "EXPR_NEUTRAL",
  "state_id": "STATE_BASE"
}
```

`characters` 仅供人读和检索，不能代替 `character_bindings[]`。含角色格还要有具体 `gaze_target / eyeline_direction / character_integrity`；含场景格要有已登记的 `scene_anchor_id` 及 `spatial_layout / lighting_anchor / axis_eyeline`；多人同格写清左右、前后景、遮挡和接触点。

跨话状态可单独审计：

```bash
python3 skills/comic-review/scripts/continuity_audit.py "创作区/画漫画/作品名" --through-chapter 第1话 --write --strict
```

### 4. 身份注册、多视图技术齐套和人审签收

```bash
python3 skills/comic-identity/scripts/registry_v2.py "创作区/画漫画/作品名" migrate --json
python3 skills/comic-identity/scripts/registry_v2.py "创作区/画漫画/作品名" migrate --write --json
python3 skills/comic-identity/scripts/identity.py "创作区/画漫画/作品名" --chapter 第1话 views \
  --backend auto --characters CHAR_A --views front,three_quarter,side,back,face
python3 skills/comic-identity/scripts/model_pack.py "创作区/画漫画/作品名" check --write --json
python3 skills/comic-identity/scripts/model_pack.py "创作区/画漫画/作品名" signoff \
  --characters CHAR_A --confirm-all --reviewer "责任编辑" --reason "并排复核通过" --json
```

- `identity_registry.json` schema v2 是角色、形态、服装、表情、状态及 LOC/PROP/STYLE/VFX 的机器真值；真实参考图只放 `出图/共享/图片/`。
- 新项目由 `init_project.py` 先写入无伪造资产/无伪造 ready 状态的合法空 v2 registry；角色定名后再由 `comic-identity` upsert 稳定 ID 与结构化形态/服装/表情/状态。
- 多视图按 `library_tier` 验收：`core_full` 为 front / three_quarter / side / back / face，`recurring_standard` 为 front / three_quarter / face，`named_minimal` 为 front / face。角色 DNA 和禁漂移项不因档位降低。
- “文件齐”不等于“可生产”。确定性技术检查通过后，仍要由人并排确认同一角色、视图标签、比例基线、服装标志和中性姿态；签收绑定全部必需视图 SHA，任一视图变化即 stale。

### 5. 缩略分镜/name board 与排版的 draft → review → approved

```bash
python3 skills/comic-name/scripts/build_name_board.py "创作区/画漫画/作品名" --chapter 第1话
python3 skills/comic-name/scripts/build_name_board.py "创作区/画漫画/作品名" --chapter 第1话 --submit-review
python3 skills/comic-name/scripts/build_name_board.py "创作区/画漫画/作品名" --chapter 第1话 --approve --reviewed-by "责任编辑"
python3 skills/comic-name/scripts/build_name_board.py "创作区/画漫画/作品名" --chapter 第1话 --check

python3 skills/comic-layout/scripts/build_layout.py "创作区/画漫画/作品名" --chapter 第1话
python3 skills/comic-layout/scripts/build_layout.py "创作区/画漫画/作品名" --chapter 第1话 --submit-review
python3 skills/comic-layout/scripts/build_layout.py "创作区/画漫画/作品名" --chapter 第1话 --approve --reviewed-by "责任编辑"
python3 skills/comic-layout/scripts/build_layout.py "创作区/画漫画/作品名" --chapter 第1话 --check
```

首次运行只生成 draft。由人工或用户明确授权的制作代理审阅页流、翻页钩子、格子轻重、阅读方向、气泡占位、关键动作和安全框后才能提交并批准；批准收据绑定产物主体及上游 SHA。代理审阅必须有项目内授权文件，且不得跳过确定性阻断。任何主体或上游变化都会使批准失效，必须重建或重新签收。

### 6. 原稿收尾、逐格参考处方和出图 job

```bash
python3 skills/comic-finishing/scripts/build_finishing_plan.py "创作区/画漫画/作品名" --chapter 第1话
python3 skills/comic-finishing/scripts/build_finishing_plan.py "创作区/画漫画/作品名" --chapter 第1话 --check
python3 skills/comic-image/scripts/reference_planner.py "创作区/画漫画/作品名" 第1话 --write
python3 skills/comic-image/scripts/build_panel_jobs.py "创作区/画漫画/作品名" --chapter 第1话
python3 skills/comic-image/scripts/build_panel_jobs.py "创作区/画漫画/作品名" --chapter 第1话 --check
```

- `finishing_plan.json` 必须消费已签收 name/layout，并同序覆盖全部 panel/page；传统原稿流程开启时，空计划或上游 SHA 过期会阻断。
- reference plan 先公平保留每个具名角色身份锚，再保留 LOC 和常驻 PROP；缺绑定、未知状态、关键真实参考缺失或超过后端附件上限时必须返工或拆格，不能静默删约束。
- `panel_jobs.json` 必须记录 reference plan、选中图片 SHA、`execution_input_sha256` 和 `consumed_contracts`；`--check` 证明落盘 job 与当前合同一致。

### 7. 阶段 gate、出图、合成和审查

```bash
python3 skills/comic-review/scripts/gate.py "创作区/画漫画/作品名" --chapter 第1话 --stage image_preflight
python3 skills/comic-image/scripts/codex_panel_runner.py "创作区/画漫画/作品名" --chapter 第1话 --targets P001 --limit 1
python3 skills/comic-review/scripts/gate.py "创作区/画漫画/作品名" --chapter 第1话 --stage image
python3 skills/comic-compose/scripts/export_longstrip.py "创作区/画漫画/作品名" --chapter 第1话 --render --qc-slots
python3 skills/comic-review/scripts/gate.py "创作区/画漫画/作品名" --chapter 第1话 --stage compose
python3 skills/comic-review/scripts/review.py "创作区/画漫画/作品名" --chapter 第1话
python3 skills/comic-review/scripts/gate.py "创作区/画漫画/作品名" --chapter 第1话 --stage review
```

每次 gate 都会写 `生产数据/gate_receipts/<stage>_第N话.json`，其中有 `inputs_fingerprint_sha256`、verdict、报告 SHA 和当前 `panel_jobs` SHA。receipt 只能证明“这次判定对应这些输入”；上游或产物变化后必须重跑，不能复制旧 receipt。

`comic-batch` 可编排可复算步骤，但会在 name/layout draft 或 review 状态正常停下等人工或用户授权制作代理签收，也不能绕过 stale 合同和 image preflight。

### 8. 生产完成与发布就绪分离

```bash
python3 skills/comic/scripts/release_verdict.py "创作区/画漫画/作品名" 第1话 --profile internal --write --json
python3 skills/comic/scripts/release_verdict.py "创作区/画漫画/作品名" 第1话 --profile digital \
  --accept --reviewer "责任编辑" --reason "最终导出物与审查证据复核通过" --write --json
python3 skills/comic/scripts/release_verdict.py "创作区/画漫画/作品名" 第1话 --profile digital --write --json
```

- `technical_complete`：导出 manifest 有真实渲染物、文件存在且 SHA 可计算、无缺图或渲染错误。
- `production_complete`：技术完成，且 `review` gate receipt 当前有效、verdict 不是 `block`。
- `publish_ready_digital / print / commercial`：再要求 `_meta.json.rights` 的 source/font/asset 三项均显式为原创、自有、公版、已授权、开源许可或不适用；缺失、`pending`、`original_or_user_provided` 等模糊值都不算已清权。之后还需人工 `release_acceptance_第N话.json` 精确绑定当前全部导出物路径/SHA 和当前 review receipt。
- `--accept` 必须显式提供 reviewer/reason；它在其它发布预检通过后替人留存 SHA 收据，但不替代人的实际复核。脚本不发布、不改 `_进度.md`。

## 失效传播与返工边界

上游变化只重算受影响的下游，但失效不可跳过：

- 开发包、源范围或 chapter contract 变化 → 重跑 source trace、分格脚本审计及后续全部阶段 gate。
- `panel_script.json` 或 `_设置.md` 变化 → name/layout 审批可能 stale；重新检查并按需重建、重签。
- identity registry、定妆图、服装/状态或 style anchor 变化 → model-pack signoff、reference plan、panel jobs 和已生成格的参考收据重新判断；受影响格重抽。
- name/layout 变化 → finishing plan、panel jobs、合成和审查失效。
- finishing/reference plan/job 变化 → image preflight 和相关 panel 失效。
- panel 图变化 → post-QC、视觉审查签收、compose/review receipt 和 release acceptance 失效。
- lettering/layout/export 变化 → compose/review receipt 与 release acceptance 失效。

`comic-update` 负责生成最小返工计划；不要直接把整话全部重做，也不要保留已被 SHA 证明过期的批准。

## 验收原则

- **确定性事实可 block**：缺文件、schema 不合法、合同字段缺失、角色 binding 不可解析、参考图缺失、SHA stale、审批缺失、panel 覆盖不闭合、导出物缺失、权利状态不满足目标 profile。
- **启发式只能 warn/info**：节拍关键词、画面指纹、embedding 距离、相似度、色彩/构图离群和多模态模型判断不能单独成为硬阻断。需要结合 contact sheet 和原图人审；如确认误报，签收必须绑定当前 artifact SHA。
- **人审不能洗掉确定性缺件**：多视图签收、编辑审批和发布签收只覆盖人应判断的部分，不能批准不存在的文件、错误 schema、缺参考或 stale SHA。
- **真值与视图分开**：JSON/JSONL 是机器合同，人读 Markdown、SVG、contact sheet 和预览图是审查视图，不能反向覆盖机器真值。
- **正式图与候选分开**：当前采纳图只放 `panels/`，旧图和多抽候选放 `candidates/`。

## 阶段路由

| 用户意图 | 路由 |
|---|---|
| 分话、改编、分格、source trace | `comic-script` |
| 页流、翻页、缩略分镜 | `comic-name` |
| 页/条漫几何、气泡占位 | `comic-layout` |
| 墨线、黑场、网点、效果线 | `comic-finishing` |
| 定妆、多视图、角色/场景/道具参考、脸漂 | `comic-identity` |
| reference plan、prompt/job、逐格出图、重抽 | `comic-image` |
| 继续推进或批量出图 | `comic-batch` |
| 嵌字、页面/长图导出 | `comic-compose` |
| gate、质量审查、发布前裁决 | `comic-review` |
| 只读进度 | `comic-progress` |
| 上游变更后的最小返工计划 | `comic-update` |

## 不做什么

- 不用完整小说作为硬前置；原创也必须有开发合同和分格真值。
- 不让图像模型直接烘焙正文台词、空白气泡或旁白框。
- 不把像素代理或模型评分包装成确定性事实。
- 不在缺少有效项目授权时自动执行付费出图或签署审阅批准；即使存在制作代理授权，也不自动发布作品、覆盖已发布导出物或突破预算/权利/核心方向边界。
