# comic 架构与生产合同

## 设计目标

comic 以 `chapter → page/scroll_segment → panel` 为生产层级，以 panel 为最小画面单位。架构解决五件事：章节为什么这样切、人物在每格到底是谁和处于什么状态、编辑决定是否被真实签收、生成时究竟消费了哪些参考、上游变化后哪些下游必须失效。

## 与同仓成熟生产线的参考边界

本线参考同仓成熟视频生产线已验证的**生产模式**：开发包先于单话生产、结构化上游合同、逐镜/逐格参考处方、阶段 gate receipt、内容哈希驱动的最小失效传播。漫画线不 import 别线代码，也不读取别线项目状态；这些模式已经按漫画的 chapter/page-or-scroll/panel、ネーム审批、静态阅读顺序、嵌字与出版导出重新实现。这样能复用成熟经验，同时保持 comic 可单独分发，任何其它作品线缺失时主流程都不降级。

“已生成”不是完成判据。每个正式阶段都要同时具备：结构化机器真值、确定性验证、人审责任点、当前输入 SHA 收据和明确的返工入口。

## 真值分层

| 层 | 机器真值 | 人读/审查视图 | 不变量 |
|---|---|---|---|
| 项目 | `_设置.md`、`_meta.json`、`_进度.md` | doctor 报告 | 设置只经 `comic-settings` 修改；进度不是创作输入 |
| 开发 | `开发包/*.json`、`脚本/split_blueprint.json`、`开发包/signoff.json` | 分话大纲、开发包检查输出 | chapter contract 和 signoff SHA 必须当前有效 |
| 脚本 | `panel_script.json`、`source_semantics.json` | 分格说明、连续性审计 | source trace、逐格角色绑定和视觉合同闭合 |
| 身份 | `identity_registry.json`、model-pack signoff | 共享资产索引、turnaround/contact sheet | registry 是唯一身份真值；人读视图不反写 |
| 编辑 | `name_board.json`、`layout.json` | SVG 缩略分镜、layout notes | 两阶段都走 draft → review → approved |
| 工艺 | `finishing_plan.json` | finishing Markdown | 同序覆盖当前已签收脚本/name/layout |
| 出图 | `comic_reference_plan_第N话.json`、`panel_jobs.json`、panel QC | prompt 索引、参考计划 Markdown | 每个 job 可追到当前合同和真实参考 SHA |
| 合成 | `lettering.json`、`export_manifest.json` | 页面、长图、槽位接触表 | 正文后期嵌字；manifest 指向真实渲染物 |
| 审查 | gate report、gate receipt、review report、release verdict | contact sheet、预览、返修清单 | receipt 绑定当前输入；发布签收绑定成品 SHA |

`生产数据/artifact_catalog.json`、Markdown、SVG、contact sheet 和预览图均可删除重建，不得替代上述业务真值。

## 合同依赖图

```text
doctor + 生产档位
        │
        ▼
开发包 ──SHA signoff──> chapter contract ──> source trace ──> panel script
                                                        │
                                                        ├──> identity registry
                                                        │      └──> 多视图技术检查 + 人审 signoff
                                                        │
                                                        └──> name draft/review/approved
                                                               └──> layout draft/review/approved
                                                                      └──> finishing plan
identity + script + layout + finishing ──> reference plan ──> panel jobs
                                                               │
                                                               └──> image_preflight receipt
                                                                      └──> panels + post-QC
                                                                             └──> image receipt
                                                                                    └──> compose/export
                                                                                           └──> review receipt
                                                                                                  └──> release verdict
```

箭头表示消费关系，也表示失效传播方向。任何被消费文件内容变化，旧审批、计划、job 或 gate receipt 都不能继续代表当前版本。

## 章节划分合同

`脚本/split_blueprint.json` v2 是章节边界真值。每话不是“平均切若干格”，而是一个可审的叙事单位：

- `source_mode/source_spans`：改编内容从哪里来；原创明确写 `original`。
- `reader_promise`：本话承诺给读者的答案、体验或欲望推进。
- `core_conflict`：谁要什么，阻力是什么。
- `turning_point`：选择、反转、发现或关系变化。
- `payoff`：本话实际兑现了什么，而不只留悬念。
- `ending_mode`：从精确枚举选择 cliffhanger、reveal、decision、emotional_aftershock、closure 等；四格和完结短篇不强制 cliffhanger。
- `budget`：仅允许 `target` 或 `soft_range`，不得用 `hard_min/hard_max` 把平台快照变成通用剧情标准。
- `entry_state / continuity_delta[] / exit_state`：长线话次声明进入状态、逐项变化和退出状态；每个变化必须有 `entity_id / field / from / to / panel_id / reason`。

开发包三件套全部 `confirmed` 后，`开发包/signoff.json` 才能由 reviewer 对当前 SHA 签收。源文件变化、source span 变化、话次重排或合同内容变化都会使 signoff/source trace 失效。

`source_semantics.json` 负责把合同源范围转为可追踪段落并绑定合同 SHA、源文件 SHA；`panel_script.json` 通过 `source_segment_refs` 覆盖这些段。外语、文言或混合语言还要记录专名、释义、目标嵌字、歧义与改编取舍。新增原创衔接格明确标记 `adaptation_origin=original_bridge`，不能伪装成源文。

## 角色、形态和多视图合同

`出图/共享/identity_registry.json` schema v2 是身份唯一真值。角色资产至少分开：

- `forms`：年龄、物种、觉醒、受伤等可继承形态。
- `outfits`：服装结构、纹样、纽扣、配饰和禁漂移项。
- `expressions`：可复用的表情状态。
- `states`：当前 form/outfit/expression 的合法组合。
- `default_binding`：默认组合，不代表所有格都可省略绑定。

每个具名角色在 panel 内必须写独立的 `character_bindings[]`，包含 `character_id/form_id/outfit_id/expression_id/state_id`。panel 级松散 `characters`、裸显示名或单个全局 outfit 不能替代绑定。LOC/PROP/STYLE/VFX 也必须先登记，再由 reference plan 选择真实图片。

多视图生产深度按角色 `library_tier`：

| tier | 必需视图 | 适用 |
|---|---|---|
| `core_full` | front / three_quarter / side / back / face | 核心和高频角色 |
| `recurring_standard` | front / three_quarter / face | 常驻次要角色 |
| `named_minimal` | front / face | 具名低频角色 |
| `restricted_partial` | 无统一必需视图 | 明确受限资产；仍要身份锚和禁漂移说明 |

模型包放行有两层：

1. 确定性技术检查：图片存在且可读、尺寸不是占位、视图不重复冒充、全身画布/比例可比、source view 证据一致。
2. 人工并排签收：确认同一角色、视图标签准确、脸/体型/服装标志稳定、中性姿态可作为生产基线。

签收 fingerprint 覆盖全部必需视图 SHA；任一图片替换、重抽或内容变化，`ready` 自动退回 `needs_approval/needs_fix`，reference plan 与相关 panel 重新判断。

## 编辑合同与几何适配

`comic-name` 和 `comic-layout` 都是显式编辑责任点：

1. build 只生成 `workflow_status=draft`。
2. 人工审阅后 `--submit-review`。
3. 真实签收人用 `--approve --reviewed-by ...`。
4. 下游只接受 `--check` 通过的 `approved` 版本。

name 审页流、翻页钩子、格子轻重、气泡语义、视线入口/出口和原稿安全框；layout 审最终阅读顺序、矩形不重叠/不越界、正文和 SFX 槽位覆盖、关键人物/动作避让与形态对应的几何 profile。

当前确定性 layout adapter 覆盖：

- 条漫：`longstrip_single_column`。
- 左读/右读页漫：`paged_grid_ltr` / `paged_grid_rtl`。
- 四格：`yonkoma_four_rows`。

复杂跨页、破格、斜格和特殊装帧仍要人工修改并重新签收；adapter 不能替编辑决定审美。

## 原稿收尾、参考处方和 job 编译

`finishing_plan.json` 消费当前已签收 name/layout，记录有序 layer contract、逐页价值计划、逐格墨线/黑场/网点/灰阶/效果线/漫符/SFX 计划。`--check` 复核全部 panel/page 同序覆盖及上游 SHA。

reference plan 是“哪些真实图片进入每格”的唯一处方层：

- 先给每个具名角色至少一个身份锚，避免多人同格时只保留主角。
- 再保留 LOC 与常驻 PROP；STYLE/VFX 按后端能力和画面需要进入。
- 极端角度、强表情、背身、换装、动作和多人同框触发相应视图/表情/服装参考。
- 附件超过真实后端上限时明确要求拆反打、拆格或分区合成，不能静默省略关键引用。

`build_panel_jobs.py` 只消费当前 reference plan，产 schema v2 job。每格记录完整生产合同、可提交的精简 prompt、结构化 binding、选择的 reference path/SHA、`panel_plan_sha256`、`execution_input_sha256` 和 `consumed_contracts`。`--check` 通过才证明 job 包没有因脚本、layout、finishing、registry 或参考图变化而 stale。

## Gate、证据等级和收据

gate stage 为：`script / name / layout / finishing / image_preflight / image / compose / review`。每次运行都写：

- `生产数据/comic_gate_<stage>_第N话.json/md`；
- `生产数据/gate_findings_<stage>_第N话.json`；
- `生产数据/gate_receipts/<stage>_第N话.json`。

receipt 至少记录 `verdict`、`inputs_fingerprint_sha256`、报告路径/SHA 和当前 panel jobs SHA。它不是永久通行证：只要 stage 输入 fingerprint 变化就 stale。

证据分两类：

- **确定性**：文件/schema/字段/覆盖/引用存在性、审批状态、SHA、生成配方和声明状态矛盾。可形成 `block`。
- **启发式**：关键词节拍、embedding、色彩/布局/相似度、像素代理、多模态模型判断和审美离群。只能形成 `warn/info`，即使来源报告误标 block，gate 也应降级。

启发式告警必须给 contact sheet、原图或任务包供人审。误报签收绑定当前 artifact SHA；图片变化后签收自动失效。人工签收不能覆盖确定性缺件或 stale 合同。

## 生产完成与发布状态

`release_verdict.py` 保持三种状态分离：

| 状态 | 必须满足 |
|---|---|
| `technical_complete` | manifest 有真实渲染物，文件存在，无缺 panel/渲染错误 |
| `production_complete` | technical complete，且当前 `review` gate receipt 非 block |
| `publish_ready_*` | production complete，加目标 profile 权利条件和当前导出物 SHA 的人工发布签收 |

`internal` 可在没有 public release acceptance、权利仍待清理时完成内部生产；`digital/print/commercial` 要求 `_meta.json.rights.source_status/font_status/asset_status` 分别给出明确可发布依据，缺失、pending 或“用户提供”这类未证明授权的模糊值一律阻断。之后必须显式执行 `release_verdict.py --accept --reviewer ... --reason ...`。生成的 `生产数据/release_acceptance_第N话.json` 至少含 approved 状态、reviewer、approved_at、与当前全部导出物完全一致的 `artifacts[].path/sha256`，以及当前 review receipt 的路径/SHA/receipt ID/report SHA。

`--accept` 只把明确的人审决定绑定到当前证据；发布裁决不上传、不发布、不修改 `_进度.md`，也不替代人的最终责任。

## 最小失效传播表

| 变化 | 必须重算/重签 |
|---|---|
| 开发包或 split blueprint | 开发签收、source trace、script 及全部下游 gate |
| 源文件内容 | source trace、受影响 panel script 及全部下游 |
| panel script / 设置 | name → layout → finishing → reference plan → jobs → panels/compose/review |
| registry 或共享参考图 | model-pack 状态、reference plan、jobs、受影响 panel 和后续 gate |
| name | name 审批、layout 及其全部下游 |
| layout | layout 审批、finishing、jobs、compose/review |
| finishing plan | reference plan、jobs、受影响 panel/image gate |
| reference plan / jobs | image_preflight、受影响 panel、后续 gate |
| panel PNG | post-QC、视觉签收、image/compose/review receipt、release acceptance |
| lettering / export | compose/review receipt、release acceptance |

最小返工由 `comic-update` 规划；失效传播意味着“必须重新证明”，不意味着无差别重做全部资产。
