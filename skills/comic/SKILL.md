---
name: comic
description: 画漫画生产线总调度。Use when the user wants to create a comic, manga, manhua, webtoon, long-scroll comic, panel script, comic name board, page layout, traditional ink/tone/effects finishing, comic art prompts, character consistency, shared references, lettering, export, one-click production, batch panel generation, rerolling panels, update/rebuild planning, or adapt a source story or idea into comics. It initializes or inspects projects under 创作区/画漫画, reads _进度.md, and routes to comic-script, comic-name, comic-layout, comic-finishing, comic-identity, comic-image, comic-batch, comic-supervisor, comic-compose, comic-review, comic-update, or comic-progress. Triggers 画漫画, 漫画, 条漫, 页漫, 分格, 分镜, 故事板, 缩略分镜, name board, 原稿收尾, 网点, 效果线, panel, storyboard, 定妆, 脸漂, 角色一致性, 嵌字, 气泡, 长图, 漫画出图, 漫画批跑, 一键漫画, 重抽漫画格, 漫画更新, comic-update, comic.
---
> 规模统计：Skill 数 14 | SKILL.md 总行数 1765 | 目录文本总行数 69118

# comic — 画漫画生产线总调度

把故事源、点子或已有脚本推进为可审计的漫画成品。正式闭环不是“图片生成完”，而是：生产合同当前有效、编辑签收有效、逐格引用闭合、阶段 gate 无确定性阻断、导出物可复核；公开发布再单独完成权利和最终成品 SHA 签收。

comic 负责定位作品根、先读 `_进度.md` / `_设置.md`、解释当前前沿并路由；一键持续推进由 `comic-supervisor` 持有 durable loop，其余动作由各阶段 skill 执行。

详细依赖和失效传播见 `references/architecture.md`；选择点见 `references/选择点与偏好.md`。

> **一键推进默认**：新项目同时显式写入 `审阅策略=用户授权制作代理` 与 `视觉审阅策略=用户授权制作代理实际查看当前像素`。普通、可逆的分话/分格取舍、原稿收尾、参考处方和内部技术检查由当前制作代理采用有证据优势的推荐方案并留痕；视觉代理必须实际查看当前 SHA-bound contact sheet，逐轴写证据，并用 `human_signoff=false` 收据继续可逆内部生产，不能靠模型分数或自动布尔值冒充目检。旧项目显式选择 `逐阶段用户确认` / `逐图具名人工` 时继续尊重其设置。权利/敏感合规、预算包创建或扩大、不可逆发布/覆盖和最终成品具名验收始终是硬边界。

一键总控入口：

```bash
python3 skills/comic/comic-supervisor/scripts/producer.py "创作区/画漫画/作品名" --chapter 第1话
```

producer 消费 `comic-batch --next-json`、连续执行安全步骤，并经项目 adapter 派发 `story_editor/comic_writer/visual_qc_agent/quality_editor`；没有 adapter 时结构化报告缺口，不把语义创作假装成脚本命令。

## 必走生产顺序

下面是正式章节的可执行主路径。旧项目可逐步补齐，但不能用旧产物绕过当前 gate。

### 1. 能力自检、生产档位和项目状态

```bash
python3 skills/comic/doctor.py "创作区/画漫画/作品名" --write
# 生产档位按项目定，从 短篇验证 / 连载标准 / 连载高一致性 里选一个（别照抄；连载类长线角一致性优先选 连载高一致性）
python3 skills/comic/comic-settings/scripts/settings_cli.py set "创作区/画漫画/作品名" 生产档位 <生产档位>
python3 skills/comic/comic-settings/scripts/settings_cli.py audit "创作区/画漫画/作品名"
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
python3 skills/comic/comic-script/scripts/development_pack.py "创作区/画漫画/作品名" scaffold --write
python3 skills/comic/comic-script/scripts/development_pack.py "创作区/画漫画/作品名" check --strict --json
python3 skills/comic/comic-script/scripts/source_semantics_gate.py "创作区/画漫画/作品名" --chapter 第1话
python3 skills/comic/comic-review/scripts/gate.py "创作区/画漫画/作品名" --chapter 第1话 --stage script
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
python3 skills/comic/comic-review/scripts/continuity_audit.py "创作区/画漫画/作品名" --through-chapter 第1话 --write --strict
```

### 4. 身份注册、多视图技术齐套和人审签收

```bash
python3 skills/comic/comic-identity/scripts/registry_v2.py "创作区/画漫画/作品名" migrate --json
python3 skills/comic/comic-identity/scripts/registry_v2.py "创作区/画漫画/作品名" migrate --write --json
python3 skills/comic/comic-identity/scripts/identity.py "创作区/画漫画/作品名" --chapter 第1话 views \
  --backend auto --characters CHAR_A --views front,three_quarter,side,back,face
python3 skills/comic/comic-identity/scripts/identity.py "创作区/画漫画/作品名" --chapter 第1话 accept-image \
  --asset CHAR_A --variant front --reviewer "责任编辑" --reason "当前比较包逐轴复核通过"
python3 skills/comic/comic-identity/scripts/model_pack.py "创作区/画漫画/作品名" check --write --json
python3 skills/comic/comic-identity/scripts/model_pack.py "创作区/画漫画/作品名" signoff \
  --characters CHAR_A --confirm-all --reviewer "责任编辑" --reason "并排复核通过" --json
```

- `identity_registry.json` schema v2 是角色、形态、服装、表情、状态及 LOC/PROP/STYLE/VFX 的机器真值；真实参考图只放 `出图/共享/图片/`。
- 新项目由 `init_project.py` 先写入无伪造资产/无伪造 ready 状态的合法空 v2 registry；角色定名后再由 `comic-identity` upsert 稳定 ID 与结构化形态/服装/表情/状态。
- 多视图按 `library_tier` 验收：`core_full` 为 front / three_quarter / side / back / face，`recurring_standard` 为 front / three_quarter / face，`named_minimal` 为 front / face。角色 DNA 和禁漂移项不因档位降低。
- “文件齐”不等于“可生产”。identity 先逐张生成并停在 `awaiting_review`，每张用 `accept-image` 绑定当前像素、contact sheet、比较包与派生输入 SHA；签收前不得写 registry ready，也不得派生下一张。重复 `views → accept-image` 直到必需视图齐全后，再做 model-pack 并排总签收。任一像素、比较输入或 contact sheet 变化都会使逐图与 model-pack 签收 stale；确定性 block 不可人工豁免。
- 所有风格锚、人物/生物定妆、多视图、场景/道具锚、候选图、封面和逐格 master 必须统一消费 `_设置.md` 的模型/渠道/格式/画幅/分辨率合同：执行时核验并使用该后端当前最高质量正式模型与最高可用原生分辨率档，同类资产保持相同 PNG/sRGB 画布；原始 master 无损保留。低分图插值放大只能是显式 derivative，不能冒充正式 master 或身份锚；完整规则由 `comic-identity` 和 `comic-image` 分别执行。

### 5. 缩略分镜/name board 与排版的 draft → review → approved

```bash
python3 skills/comic/comic-name/scripts/build_name_board.py "创作区/画漫画/作品名" --chapter 第1话
python3 skills/comic/comic-name/scripts/build_name_board.py "创作区/画漫画/作品名" --chapter 第1话 --submit-review
python3 skills/comic/comic-name/scripts/build_name_board.py "创作区/画漫画/作品名" --chapter 第1话 --approve --reviewed-by "责任编辑"
python3 skills/comic/comic-name/scripts/build_name_board.py "创作区/画漫画/作品名" --chapter 第1话 --check

python3 skills/comic/comic-layout/scripts/build_layout.py "创作区/画漫画/作品名" --chapter 第1话
python3 skills/comic/comic-layout/scripts/layout_candidates.py "创作区/画漫画/作品名" --chapter 第1话 --apply-best
python3 skills/comic/comic-layout/scripts/build_layout.py "创作区/画漫画/作品名" --chapter 第1话 --submit-review
python3 skills/comic/comic-layout/scripts/build_layout.py "创作区/画漫画/作品名" --chapter 第1话 --approve --reviewed-by "责任编辑"
python3 skills/comic/comic-layout/scripts/build_layout.py "创作区/画漫画/作品名" --chapter 第1话 --check
```

首次进入编辑阶段先生成 draft。显式逐阶段人审项目由人工审阅页流、翻页钩子、格子轻重、阅读方向、气泡占位、关键动作和安全框后签收；delegated 项目允许 batch 先做机器结构签收以继续可逆内部流程，但收据必须标记 `delegated_policy_auto_review`，不得声称已经完成视觉/语义人审。代理授权必须由项目 `_设置.md` **显式**写入 `审阅策略=用户授权制作代理`，或持有当前有效、摘要匹配的 `生产数据/authorizations/editorial_review.json`；缺文件/缺 key 不得继承 permissive 默认。授权有效时 `comic-batch` 在同一次 run 内完成 submit/approve/check 并继续，后续真实 review/最终验收仍检查视觉与成品质量。任何主体、上游或授权变化都会使批准失效，必须重建或重新签收。

自动选版不再把普通左右页误判成跨页：`spread_id` 只表达成组页面，只有显式 `cross_page_art/spread_mode=cross_page_art` 才进入保护模式。普通条漫/页漫用实际手机 screen-beat 或左右页/page-turn SVG 的屏占比、拥挤、空屏、内侧气泡和翻页钩子信号排序并可 `--apply-best`；真实跨中缝画面仍保留编辑保护，避免自动裁断。

### 6. 原稿收尾、逐格参考处方和出图 job

```bash
python3 skills/comic/comic-finishing/scripts/build_finishing_plan.py "创作区/画漫画/作品名" --chapter 第1话
python3 skills/comic/comic-finishing/scripts/build_finishing_plan.py "创作区/画漫画/作品名" --chapter 第1话 --check
python3 skills/comic/comic-image/scripts/reference_planner.py "创作区/画漫画/作品名" 第1话 --write
python3 skills/comic/comic-image/scripts/build_panel_jobs.py "创作区/画漫画/作品名" --chapter 第1话
python3 skills/comic/comic-image/scripts/build_panel_jobs.py "创作区/画漫画/作品名" --chapter 第1话 --check
```

- `finishing_plan.json` 必须消费已签收 name/layout，并同序覆盖全部 panel/page；传统原稿流程开启时，空计划或上游 SHA 过期会阻断。
- reference plan 先公平保留每个具名角色身份锚，再保留 LOC 和常驻 PROP；缺绑定、未知状态、关键真实参考缺失或超过后端附件上限时必须返工或拆格，不能静默删约束。
- `panel_jobs.json` 必须记录 reference plan、选中图片 SHA、`execution_input_sha256` 和 `consumed_contracts`；`--check` 证明落盘 job 与当前合同一致。
- 每个具名主体的 DNA、form/outfit/expression/state/variant、exact reference 像素 SHA、bbox/mask/occlusion locator 与真实 subject binding 必须进入 `identity_execution_contracts[]` 和 execution SHA；`image_preflight` 在付费前复算，不能等出图后才发现拿错形态或服装。
- 漫画出图默认执行 `_设置.md` 的 `生图分辨率策略=后端最高可达`：每格独立请求当前后端最高质量正式模型及最高原生档并保留 master，排版只可向下采样。整页/整话低宽图裁格后放大、丢失原始 master、或用放大后的像素尺寸冒充高清，均不得通过 image QC。
- 正式像素按 immutable provider raw → atomic active master → layout derivative 保存，并记录 color space/bit depth/ICC/alpha/derivative chain。关键格默认在同一阶段预算 envelope 内顺序生成少量候选；每张独立走当前像素 B14，达到目标数后按结构化逐轴 warning 最少的规则自动采用并写 manifest/adoption receipt。
- 局部修手、表情、道具或服装走 `comic-finishing/scripts/local_repair_transaction.py`：事务绑定 source master/mask/bbox/prompt/execution SHA，只允许 mask 内像素变化；失败回滚，成功后旧 B14 自动失效并重新目检，不整格无痕覆盖。

### 7. 阶段 gate、出图、合成和审查

```bash
python3 skills/comic/comic-review/scripts/gate.py "创作区/画漫画/作品名" --chapter 第1话 --stage image_preflight
python3 skills/comic/comic-image/scripts/codex_panel_runner.py "创作区/画漫画/作品名" --chapter 第1话 --targets P001 --limit 1
python3 skills/comic/comic-image/scripts/codex_panel_runner.py "创作区/画漫画/作品名" --chapter 第1话 --targets P001 \
  --accept-reviewed --reviewer "责任编辑" --review-notes "当前 panel 与比较包逐轴复核通过"
# 项目选择 Dreamina/即梦官方 CLI 时：
python3 skills/comic/comic-image/scripts/dreamina_panel_runner.py "创作区/画漫画/作品名" --chapter 第1话 --targets P001 --max-attempts 2
python3 skills/comic/comic-review/scripts/gate.py "创作区/画漫画/作品名" --chapter 第1话 --stage image
python3 skills/comic/comic-compose/scripts/export_longstrip.py "创作区/画漫画/作品名" --chapter 第1话 --render --qc-slots
python3 skills/comic/comic-review/scripts/gate.py "创作区/画漫画/作品名" --chapter 第1话 --stage compose
python3 skills/comic/comic-review/scripts/review.py "创作区/画漫画/作品名" --chapter 第1话
python3 skills/comic/comic-review/scripts/gate.py "创作区/画漫画/作品名" --chapter 第1话 --stage review
```

每次 gate 都会写 `生产数据/gate_receipts/<stage>_第N话.json`，其中有 `inputs_fingerprint_sha256`、verdict、报告 SHA 和当前 `panel_jobs` SHA。receipt 只能证明“这次判定对应这些输入”；上游或产物变化后必须重跑，不能复制旧 receipt。

逐格 runner 是严格顺序闸：一次只生成当前格，机器 pass/warn 都先进入当前像素审阅；只有绑定当前像素、post-QC、contact sheet、比较包及每个输入 SHA 的具名人审，或当前授权的视觉代理实际目检收据，才允许下一格。结构化结果逐轴含 verdict/evidence/notes，身份轴还要逐主体定位；普通 review note 不再自动把所有轴填 true。代理收据必须写 `human_signoff=false + authorization`；授权撤销、像素或比较输入变化后自动失效，确定性 block 永不可签。

`comic-batch` 可编排可复算步骤；若项目为 `逐阶段用户确认`，会在 name/layout draft 或 review 状态等待人工；默认 `用户授权制作代理` 下，当前 agent 必须接管实际审阅、证据化签收并在同一任务继续，不能把这个内部代理节点升级成用户停点。两种模式都不能绕过 stale 合同、image preflight 与逐格当前像素验收。

### 8. 一个状态、一个哈希、一个完成定义

```bash
python3 skills/comic/scripts/release_verdict.py "创作区/画漫画/作品名" 第1话 --profile internal --write --json
python3 skills/comic/scripts/release_verdict.py "创作区/画漫画/作品名" 第1话 --profile digital \
  --accept --reviewer "责任编辑" --reason "最终导出物与审查证据复核通过" --write --json
python3 skills/comic/scripts/release_verdict.py "创作区/画漫画/作品名" 第1话 --profile digital --write --json
python3 skills/comic/scripts/release_verdict.py "创作区/画漫画/作品名" 第1话 --medium print_pdf --usage commercial --write --json
python3 skills/comic/scripts/release_verdict.py "创作区/画漫画/作品名" 第1话 --profile internal \
  --accept-final --reviewer "责任编辑" --reason "最终成品实际复核通过" --write --json
```

- `生产数据/release_contract_第N话.json` 是唯一 active delivery contract；其它轴报告归档到 `release_verdicts/`，只是历史证据。
- 当前有序导出物、review receipt、warning dispositions、平台 preview、介质合同、权利与 provenance 聚合成唯一 `release_digest`。不可变 release bundle 同时冻结这些证据，active pointer 最后切换；任一字节/合同变化使旧最终签收失效。
- `生产数据/completion_verdict_第N话.json` 只有 `blocked | machine_ready | accepted`；只有 `accepted` 是最终完成。`_进度.md`、dashboard、provider succeeded、旧 `delivery_states` 都是派生视图。
- `medium=web_images|print_pdf|epub_fxl` 与 `usage=internal|public|commercial` 解耦。Pillow PDF 只到 raster readiness；PDF/X-4 必须由注册专业 adapter 生成并让 validator receipt 精确绑定 staged PDF、合同、ICC 和有序页面输入 SHA。`build_epub_fxl.py` 以组三文件事务原子提升 EPUB+合同+manifest，写正确 RTL/LTR spine，并可嵌入有序 panel/dialogue/narration/SFX 语义稿；人工语义复核不冒充无障碍认证。
- 公开/商用还要求 `_meta.json.rights` 明确清权、目标平台实际缩略图/后台预览（profile 有一手证据时）、当前 warning disposition ledger 全结案且哈希链完整。`release_acceptance_第N话.json` 精确绑定全部导出物、review receipt、有序平台 preview、处置账，以及当前印刷/EPUB 介质合同和收据；任一项变化均需重签。
- provenance hash chain/JSON sidecar 只代表披露，不代表签名。只有 `comic_c2pa_sign_v1` adapter 嵌入 manifest、验证器精确绑定 source/signed asset SHA 后，ledger 才写 `c2pa_status=signed`；见 `references/provenance_and_credentials.md`。
- `--accept` 记录公开/商用发布签收；`--accept-final` 记录内部交付的具名最终验收。二者都不能由 `delegate:` 执行，也不自动发布。

## 失效传播与返工边界

上游变化只重算受影响的下游，但失效不可跳过：

- 开发包、源范围或 chapter contract 变化 → 重跑 source trace、分格脚本审计及后续全部阶段 gate。
- `panel_script.json` 或 `_设置.md` 变化 → name/layout 审批可能 stale；重新检查并按需重建、重签。
- identity registry、定妆图、服装/状态、style anchor 或逐图比较包变化 → 逐图/model-pack signoff、reference plan、panel jobs 和真实消费它的格重新判断。
- name/layout 变化 → finishing plan、panel jobs、合成和审查失效。
- finishing/reference plan/job 变化 → image preflight 和相关 panel 失效。
- panel 图或其 comparison/contact sheet 变化 → post-QC、视觉审查签收、compose/review receipt 和 release acceptance 失效。
- 原句/翻译/lettering/layout/export 变化 → 由逐格依赖索引定位消费它的格/页，compose/review receipt 与 release acceptance 失效。
- 平台顺序/preview、PDF/EPUB、介质合同或 readiness receipt 变化 → 对应 preview/medium binding 与 release acceptance 失效。

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
| 一键持续推进、专家派发、断点续跑 | `comic-supervisor` |
| 嵌字、页面/长图导出 | `comic-compose` |
| gate、质量审查、发布前裁决 | `comic-review` |
| 只读进度 | `comic-progress` |
| 上游变更后的最小返工计划 | `comic-update` |

## 不做什么

- 不用完整小说作为硬前置；原创也必须有开发合同和分格真值。
- 不让图像模型直接烘焙正文台词、空白气泡或旁白框。
- 不把像素代理或模型评分包装成确定性事实。
- 不在缺少有效项目授权时自动执行付费出图或签署审阅批准；即使存在制作代理授权，也不自动发布作品、覆盖已发布导出物或突破预算/权利/核心方向边界。
