# 漫画生产与发布验收 Checklist

使用方式：先逐项确认确定性合同，再处理启发式告警。`[BLOCK]` 可阻断对应 stage；`[WARN]` 必须查看证据、返修或做当前 SHA 的人审签收，但不能单独升级为硬阻断。

## 0. 能力与设置

- [ ] `[BLOCK]` 已运行 `comic/doctor.py`，知道当前是 full / degraded / none；缺可选视觉依赖时没有伪称已完成像素级判断。
- [ ] `[BLOCK]` `_设置.md` 有受支持的 `生产档位`，且档位联动的定妆、形态继承、一致性硬闸等值一致。
- [ ] `[BLOCK]` `comic-settings audit` 无 error；模型、渠道、格式、语言、目标平台和合规用途没有占位值。
- [ ] `[BLOCK]` 付费、覆盖正式图、公开发布等动作已分别获得当次授权。

## 1. 开发包与章节划分

- [ ] `[BLOCK]` `adaptation_strategy.json`、`season_arc.json`、`split_blueprint.json` 均为 v2、合法 JSON、`status=confirmed`，无 TODO/待补占位。
- [ ] `[BLOCK]` `开发包/signoff.json` 有 reviewer、role、time，并精确绑定三件套当前 SHA。
- [ ] `[BLOCK]` 话次连续且唯一；每话有 `chapter_type / format_profile / source_mode`。
- [ ] `[BLOCK]` 每话有 `reader_promise / core_conflict / turning_point / payoff / ending_mode`。
- [ ] `[BLOCK]` `budget` 只有 target/soft_range 等软意图，没有 `hard_min/hard_max`。
- [ ] `[BLOCK]` 改编话次 `source_spans` 指向作品根内真实文件；未说明的缺口、重叠、倒序或整文件重复消费已消除。
- [ ] `[BLOCK]` 原创话次明确 `source_mode=original` 且不伪造 source spans。
- [ ] `[BLOCK]` 长线话次有非空 `entry_state / continuity_delta[] / exit_state`；每个 transition 有 `entity_id / field / from / to / panel_id / reason`。
- [ ] `[WARN]` 话末 ending mode 与本话实际兑现相符；四格、完结短篇和情绪落点没有被通用 cliffhanger 模板绑架。
- [ ] `[WARN]` 格数/页数仅用于产能估算，章节边界确实由戏剧闭环决定。

## 2. Source trace 与分格脚本

- [ ] `[BLOCK]` `source_semantics.json` 绑定当前 chapter contract SHA 和源文件 SHA，没有 stale reason。
- [ ] `[BLOCK]` 需要语言归一化时，source language、目标文字语言、专名、释义、歧义和改编取舍均已完成。
- [ ] `[BLOCK]` 每个改编 panel 的 `source_segment_refs` 有效；新增衔接格标记 `adaptation_origin=original_bridge` 并说明原因。
- [ ] `[BLOCK]` `panel_script.json.chapter_contract_sha256` 等于当前本话合同规范 SHA。
- [ ] `[BLOCK]` panel ID 唯一、有序，且每格有 story function、description、dialogue/narration/SFX/art notes 的合法结构。
- [ ] `[BLOCK]` 顶层 `visual_contract` 有风格基线、场景锚和人物完整性策略。
- [ ] `[BLOCK]` 含角色格有逐角色 `character_bindings[]`，每项含 `character_id/form_id/outfit_id/expression_id/state_id`；裸名字没有冒充 binding。
- [ ] `[BLOCK]` 含角色格有具体戏内 `gaze_target`、`eyeline_direction` 和 `character_integrity`；除明确 POV/破第四墙外不无理由看镜头。
- [ ] `[BLOCK]` 含场景格 `scene_anchor_id` 已登记为 LOC，并有可执行 `spatial_layout / lighting_anchor / axis_eyeline`。
- [ ] `[BLOCK]` 多人同格写清左右、前后景、遮挡、接触点和视线轴线。
- [ ] `[BLOCK]` continuity audit 中上一话 exit 与下一话 entry 一致；每个状态变化证据 panel 存在；computed exit 等于 declared exit。
- [ ] `[WARN]` 首格有明确阅读动作，末格形成对应 ending intent；旁白不只是复述画面。
- [ ] `[WARN]` 重复台词、事实复述、构图计划和高潮位置告警已人工判断。

## 3. Identity Registry 与模型包

- [ ] `[BLOCK]` `identity_registry.json` 为 schema v2，资产 ID/类型合法；角色 forms/outfits/expressions/states/default_binding 引用闭合。
- [ ] `[BLOCK]` 角色 DNA 覆盖脸型、眼型/眼距、发际线/发型轮廓、体型、服装主色、标志配饰/伤痕和禁漂移项。
- [ ] `[BLOCK]` 临时手持物、当格站位、注视目标没有固化为永久身份 DNA。
- [ ] `[BLOCK]` 每个 binding 的 state 与 form/outfit/expression 一致；换装格有对应 outfit 登记和真实服装参考。
- [ ] `[BLOCK]` 核心/常驻/具名角色按 `library_tier` 补齐必需视图：core 五视图、recurring 三视图、named 两视图。
- [ ] `[BLOCK]` 必需视图都是可读真实图片，不是 1×1 占位、重复图片冒充不同视角、错误 source view 或不可比较画布。
- [ ] `[BLOCK]` 核心模型包已由真实 reviewer 并排签收；signoff fingerprint 与当前全部必需视图 SHA 一致。
- [ ] `[BLOCK]` LOC 是无人物纯场景锚；关键 PROP、STYLE、VFX 有可解析真实图片和禁继承说明。
- [ ] `[WARN]` 人审确认所有视图是同一角色，脸/体型/服装标志稳定，视图标签准确、姿态中性。
- [ ] `[WARN]` 低频/受限角色降低视图数量时，角色 DNA 和禁漂移项没有同步降级。

## 4. 缩略分镜/name board 签收

- [ ] `[BLOCK]` `name_board.json` 为 schema v2，panel 唯一且同序覆盖脚本。
- [ ] `[BLOCK]` `page_hint` 要么全部提供要么全部省略；填写时为整数且按阅读顺序单调不减。
- [ ] `[BLOCK]` `workflow_status=approved`，approval 有真实 reviewed_by/时间，subject SHA 与当前 board 一致，上游 panel script/设置 SHA 当前。
- [ ] `[WARN]` 页漫的 page side、spread、翻页 setup/payoff 可读；条漫的滚动停顿和呼吸合理；四格顺序明确。
- [ ] `[WARN]` 大格服务揭示、动作峰值、情绪或钩子，不是平均放大。
- [ ] `[WARN]` 气泡优先级和 subject/avoid regions 不会预设遮脸、手、关键道具或接触点。
- [ ] `[WARN]` trim/safe/bleed/inner frame 足以支持目标原稿规格。

## 5. Layout 签收

- [ ] `[BLOCK]` `layout.json` 为 schema v2，消费当前已签收 name；panel 唯一、同序、无缺失。
- [ ] `[BLOCK]` geometry profile 与漫画形态/阅读方向一致：条漫单列、LTR/RTL 页漫网格、四格四行。
- [ ] `[BLOCK]` 矩形不越界、不重叠；reading order 唯一连续。
- [ ] `[BLOCK]` 每段正文、旁白和 SFX 都有界内 bubble slot；槽位引用有效。
- [ ] `[BLOCK]` `workflow_status=approved`，approval subject SHA 当前；panel script/name/settings 任一变化后已重新检查或重签。
- [ ] `[WARN]` 气泡不挡脸、身份标志、手脚、动作接触点和剧情道具。
- [ ] `[WARN]` 复杂跨页、破格、斜格或特殊装帧已经人工调整和重新签收，没有只靠基础 adapter 假装完成。
- [ ] `[WARN]` 文字过多时回脚本压缩，没有靠极小字号硬塞。

## 6. 原稿收尾

- [ ] `[BLOCK]` 传统原稿流程开启时存在 `finishing_plan.json`，且 `workflow_status=validated`。
- [ ] `[BLOCK]` plan 精确绑定当前 panel script、已签收 name/layout 和设置 SHA；panel/page 唯一同序覆盖。
- [ ] `[BLOCK]` 每格有有序 layer contract，以及 ink/black/value-or-tone/effects 所需项目；每个 SFX 绑定源内容引用。
- [ ] `[WARN]` 黑场服务焦点和情绪，不遮识别特征、手脚、关键道具或接触点。
- [ ] `[WARN]` 网点/灰阶服务材质、空间和价值层级，不把主体、背景和文字留白糊成一层。
- [ ] `[WARN]` 速度线、集中线、冲击闪、漫符和手绘拟声词指向动作路径、焦点或情绪读点。

## 7. Reference Plan 与 Panel Jobs

- [ ] `[BLOCK]` reference plan 的输入 fingerprint、plan SHA 和所有真实图片 SHA 当前。
- [ ] `[BLOCK]` 每个具名角色在每格至少保留一个真实身份锚；多人同格没有因预算只保留主角。
- [ ] `[BLOCK]` 需要的 LOC、常驻 PROP、换装、强表情和极端角度参考已选择；关键参考文件存在。
- [ ] `[BLOCK]` 超过后端真实附件上限时已经拆反打、拆格或制定分区合成，未静默丢弃关键约束。
- [ ] `[BLOCK]` `panel_jobs.json` 为 schema v2，panel 覆盖完整；每格含结构化 bindings、reference path/SHA、`panel_plan_sha256`、`execution_input_sha256`、`consumed_contracts`。
- [ ] `[BLOCK]` `build_panel_jobs.py --check` 没有 stale/missing panel；提交 prompt 来自当前 compiler/profile。
- [ ] `[WARN]` 低风险被省略附件已在 bundle 中留痕，文字合同仍保留约束。

## 8. 出图与 Post-QC

- [ ] `[BLOCK]` 当前 `image_preflight` receipt 非 block，且 `inputs_fingerprint_sha256`/panel jobs SHA 当前。
- [ ] `[BLOCK]` 每个必需 panel 文件存在、可解码，job 状态为 ready；生成记录的 execution input SHA 与当前 job 一致。
- [ ] `[BLOCK]` 确定性 post-QC 没有图片损坏、空文件、错误尺寸或明确不可用状态。
- [ ] `[BLOCK]` 正式图只在 `panels/`，旧图/候选在 `candidates/`；重抽没有覆盖审计历史。
- [ ] `[WARN]` 人物脸、发型、体型、服装和标志物跨格稳定；动作格手脚归属和道具接触清楚。
- [ ] `[WARN]` 同一 LOC 的建筑结构、门窗、光向/冷暖、轴线、常驻道具和人物左右关系连续。
- [ ] `[WARN]` 单格没有意外拼贴 gutter、照片墙、内部分栏、截图边或空白气泡。
- [ ] `[WARN]` 风格/角色/场景/道具 contact sheet、embedding/像素离群和 near-duplicate 告警都已查看原图。
- [ ] `[WARN]` VLM verdict 同时匹配当前 panel SHA、task SHA、全部 reference SHA 和 evaluator model/version；否则忽略旧裁决。
- [ ] `[WARN]` 误报签收含 reason/evidence/current artifact SHA；重抽后重新审。

## 9. 嵌字与导出

- [ ] `[BLOCK]` 正文台词/旁白由 `lettering.json` 后期渲染，面板图未烘焙正文或无字气泡。
- [ ] `[BLOCK]` `export_manifest.json` 存在、无 `missing_panels`/`render_error`，`rendered[]` 指向真实文件。
- [ ] `[BLOCK]` `lettering_slot_qc` 存在且 `missing_slots=[]`；文字语言与设置/manifest 一致。
- [ ] `[BLOCK]` 目标平台有已核验 profile 时，宽高、格式、大小、页/格数硬规格通过；未核验规格不能宣称可投稿。
- [ ] `[WARN]` 移动端字号可读，双语顺序统一，英文扩张后仍不越界。
- [ ] `[WARN]` 气泡尾指向清楚，不挡脸、手、身份标志、剧情道具和动作落点；拟声词不破坏动作可读性。
- [ ] `[WARN]` 页/长图阅读顺序、分段位置、留白和翻页效果已看真实渲染物，而不只看 manifest。

## 10. 综合审查与 Receipt

- [ ] `[BLOCK]` `script/name/layout/finishing/image_preflight/image/compose/review` 所需 stage 均有对应当前输入的 gate receipt。
- [ ] `[BLOCK]` receipt 的 `verdict` 不是 block；“receipt 文件存在”没有被误当作通过。
- [ ] `[BLOCK]` receipt 报告 SHA 可复核，stage 输入 fingerprint 与当前文件一致。
- [ ] `[WARN]` 所有 warn 已被分配为：返修、带证据接受、或明确保留到内部草稿；没有无主告警。
- [ ] `[WARN]` `comic_review_第N话` 已人工看过页面/长图成品、关键 contact sheet 和高风险原图。
- [ ] `[WARN]` `_进度.md` 只在真实阶段完成后更新；报告 pass 但用户未要求时不自动写进度。

## 11. 生产完成与发布

- [ ] `[BLOCK]` `technical_complete=true`：最终导出物真实存在，manifest 无缺图/渲染错误。
- [ ] `[BLOCK]` `production_complete=true`：technical complete，且当前 review gate receipt 非 block。
- [ ] `[BLOCK-public]` `_meta.json.rights` 的 source/font/asset 三项均为明确清权状态；缺失、pending、仅声明“用户提供”都不可公开/印刷/商用。
- [ ] `[BLOCK-public]` `release_acceptance_第N话.json` 有 approved 状态、真实 reviewer、approved_at。
- [ ] `[BLOCK-public]` acceptance 的 `artifacts[].path/sha256` 与当前全部导出物完全一致；任何导出变化后重新签收。
- [ ] `[BLOCK-public]` acceptance 的 `review_receipt` 与当前 review receipt 的路径/SHA/receipt ID/report SHA 完全一致；重跑 review 后重新签收。
- [ ] `[BLOCK-public]` 签收由真实 reviewer 显式运行 `release_verdict.py --accept --reviewer ... --reason ...`，不是脚本自我批准。
- [ ] `[BLOCK-public]` `release_verdict.py --medium web_images|print_pdf|epub_fxl --usage public|commercial` 的对应 `publish_ready_*` 为 true；旧 `--profile` 仅作兼容映射。
- [ ] `[BLOCK-print]` print_pdf 有真实 PDF、trim/bleed/safe/DPI/页序装订/字体/ICC/透明度合同，及绑定当前合同/PDF SHA 的印前人审 receipt；普通图片包未冒充印刷交付。
- [ ] `[BLOCK-platform]` profile 明确支持 viewport preview 时，PC/mobile 截图来自 `actual_platform_preview`，不是 local simulation，并绑定当前全部交付物 SHA。
- [ ] `[BLOCK-public]` 当前 review warning 已逐条 disposition，release acceptance 绑定 disposition summary/ledger SHA；处置账变化后已重签。
- [ ] `[BLOCK-epub]` epub_fxl 是结构有效的真实 EPUB，reading order/text alternatives/navigation/accessibility metadata 齐；结论仅为 human-attested workflow readiness，未冒充 EPUB Accessibility/WCAG 认证。
- [ ] `[WARN]` internal 完成没有被宣传成公开发布就绪；生产完成、发行批准和实际发布动作保持分离。
- [ ] `[WARN]` `release_verdict.py` 只生成裁决证据，没有被误认为已经上传或发布。

## 12. 变更后的失效检查

- [ ] 开发包/源/合同变化后：重跑 source trace、script 和全部受影响下游 gate。
- [ ] 脚本/设置变化后：重查 name/layout approval，并重建 finishing/reference plan/jobs。
- [ ] registry/定妆/服装/状态/风格锚变化后：重查 model-pack signoff、reference plan、jobs 和受影响 panel。
- [ ] name/layout 变化后：finishing、jobs、compose/review 及发布签收已失效并重算。
- [ ] panel 重抽后：post-QC、视觉告警签收、image/compose/review receipt 和 release acceptance 已重算。
- [ ] lettering/export 变化后：compose/review receipt 和 release acceptance 已重算。
- [ ] 使用 `comic-update` 生成最小返工计划；没有因为一个局部 SHA 变化无差别重做整话，也没有保留已失效批准。
