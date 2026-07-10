# Skill 设计原则（设计宪法）

> **这是本仓库唯一的「怎么*建造* skill」权威法条**（authoring-time constitution）。
> 跨工具、随仓库交付、对所有六条线（novel / n2d / comic / song / mv / ad）生效。
>
> **三层分工，别放错层：**
> | 层 | 管什么 | 住在哪 |
> |---|---|---|
> | **设计宪法**（本文件）| 怎么*建造*一个 skill：独立性、选择点、合规、交付约束 | **本文件，单一副本** |
> | **运行期契约** | skill *执行*时的 manifest 字段、阶段表、候选清单 | 各线 `*-craft/` / 本线 `_lib/` / 本线 `references/选择点与偏好.md` |
> | **机器/会话事实** | 这台机器、此刻为真（env 缺失、后端宕机）| 各 AI 的私有 memory / 本机配置（不随交付）|
>
> 入口文档（`CLAUDE.md` / `AGENTS.md` / `GEMINI.md`）只放 ~5 行摘要 + 指回本文件，**不复述**。
> 各线 `*-craft/SKILL.md` 的 `## 设计原则` 只留**本线特有**原则 + 一行指针，通用条文不再各抄一份。
> 标 ✅ 的条文已有机器检查覆盖（`tools/validate_skills.py` 或对应专项审计）；标 ◑ 的部分机检；其余靠 review。

---

## A. 仓库形态与独立性

- **A1 六线自包含、可单独分发** ✅ — 每条线本线脚本只 import 本线 `_lib`/craft 工具，**不依赖 `skills/common/`**（已删），**不 import 别线实现**。novel 与 n2d 之间必须零交接、零数据耦合；其它跨线交付只能是用户显式选择的成品文件交接，交接缺失必须**优雅降级**，不能让本线主流程跑不起来。**独立性延伸到散文**：`skills/<line>/**.md` 不得提别线名/别线根标签/别线 skill —— 这条 strict-docs 门已是 `check_independence.py` 的**默认行为**（`--lenient-docs` 仅在确有需要时降级为只查代码级耦合）。机检：`tools/independence-audit/scripts/check_independence.py`，novel/n2d 另跑 `tools/independence-audit/scripts/check_novel_n2d_zero_coupling.py`。
- **A2 仓库级 meta 工具放 `tools/`，不放 `skills/`** — 不是某条创作线能力的单副本维护工具（independence-audit、shared-cleanup、validate_skills、打包/发布脚本等）留 `tools/` 或独立单副本，不混进 `skills/` 的创作线命名空间。**例外**：属于某条线用户工作流的一线能力（如 `n2d-progress`）仍是该线 skill，可以留在 `skills/`。
- **A3 `skills/` 扁平、按名字前缀分组** — `n2d-*` / `song-*` 等。SKILL.md frontmatter `description` + 正文 `Triggers`/`Use when` **就是路由依据**，匹配用户意图，不另建路由表逻辑。

## B. Skill 编写法

- **B1 脚本通用、无专有 API** — 纯 Python / bash，只调通用工具（`ffmpeg`/`librosa`/`whisper`/`yt-dlp`/生图生视频 CLI）；不绑定任何一家 AI 的专有 SDK；引用路径用中立的 `skills/...`。
- **B2 推荐 skill 一律写裸名** ✅ — 输出「下一步」或推荐调用时写 `n2d-image`，**不写** `/n2d-image`（有些 agent 把 `/...` 当内置斜杠命令报错）。
- **B3 prompt / 产物分离** — prompt 包与生成产物分目录、分文件，不混写。
- **B4 脚本不伪装云端自动化** — 没有凭证/后端 SDK 时，只产稳定 prompt/job 包 + 合规留痕；真正调用 Suno/即梦/Kling 等交对应后端工具，外部生成后再登记。
- **B5 阶段完成即回写 `_进度.md`** — 用确定性脚本（`progress_set.py` / `update_progress_stage()`）回写，不只在文档里说「更新进度」。正式产物阶段默认先过 `gate.py`。
- **B6 高风险连续性铁律必须机器化** ◑ — 跨阶段/跨帧/高成本的身份、资产、合规、成本规则不得只写在 SKILL.md 里靠人记；必须有确定性 gate、生产入口 guard 或回归测试覆盖，且正式产物入口不能提供无保护绕过。**n2d 图生视频非协商例**：同一角色多关键帧 Clip 的首/中/尾锚图必须来自同一个 `identity_registry` 角色/形态和同一套可执行 `reference_group`，prompt 必须绑定 `CHAR_xx/形态`、`reference_group=<同源组>`、脸型/眼距/鼻梁/下颌/发型发髻/标志配饰/服装配色等身份不变量；大表情近景必须使用同源 `reference_group.expressions` 或表情定妆首尾双帧，并写 `表情锚`、`表情幅度`、`锁脸不锁情`。后端支持 Character ID / Face Lock / reference controls / LoRA 时必须同时传原生身份；不支持时只能转入**保真实现分解**（降低运动幅度、缩小景别、侧脸/手部/反应镜、拆 Clip、分区构建等），但不得删戏、砍人物、改变动作目标或弱化剧情/情绪功能。未来改 skill 不得删除、绕过或弱化这类铁律；若确需重构，只能用等价或更严格的确定性机检 + 回归测试替换。
- **B7 分档人物定妆基础包不可缺失铁律 / Clip 图前分档资产基础包铁律** ✅ — n2d 中所有入镜具名人物都必须有作品根 `角色库/<CHAR_ID>__<slug>/manifest.json`，但资产生产深度不得一刀切。`library_tier` 固定为四档：`core_full`（主角/核心长线/计划出场≥10集）要求 `front/three_quarter/side/back` + `half_body|full_body|outfit` + `face_anchor_refs|expressions` + `turnaround`；`recurring_standard` 要 `front/three_quarter` + body/outfit + face anchor，侧背按镜头补；`named_minimal` 要 `front` + body/outfit + face anchor，近景/转头/过肩/侧背/多集复用时升档；`restricted_partial` 只建允许的手部/肩背/服装/剪影局部。该档位只控制资产深度，不替代主体 ID/face embedding/LoRA 身份锁档。已有拆分 PNG 必须同源派生：45°/侧/背从同一人审母本派生，半身/脸锚从已通过正面裁切，`ready` 登记 `derivation.method/source_path/source_sha256/crop_box`；`planned` 不能冒充本档或本镜必需项。任何 Clip PNG 生成前，本集共享资产必须先满足**所属档位 + 当前镜头实际需求**及 registry 约束；场景/道具/武器/VFX 仍须先有参考与结构锁，核心武器须 `weapon_profile`。缺本档/本镜必需项时只能补共享层，**不得生成 Clip 分镜图**；共享库先行顺序不可被 `--skip-preflight`、P0 垂直切片、抽样或局部 `--shots` 绕过。机器覆盖：tier-aware `check_identity_registry` / `reference_planner` 与 `core_full/recurring_standard/named_minimal/restricted_partial` 回归测试、同源派生、`enforce_shared_first_interlock`、prompt/checklist 和 `tools/validate_skills.py --only B7`。
- **B8 分集叙事连续性铁律** ◑ — 凡做拆集、分集、分段剧本的 skill，**不得设置单集时长硬性上限或下限**，也不得为了凑时长/字数把一场戏、一个爽点或一个 cliffhanger 劈断。时长只能是软节奏意图、容量估算或统计 WARN；最终边界必须优先服从剧情连贯性与完整闭环。每集至少完成 **冲突 → 爽点/反转 → 钩子** 的戏剧闭环，允许短集或长集，只要闭环成立且下一集能冷开场。粗拆脚本只能产脚手架，正式写词前必须用确定性边界预筛或等价 guard 把「章内续切、弱钩、半句、纯过渡、短/长但无闭环」标出；高风险窗口未写边界复核记录时，不得进入正式 voiceover/分镜定稿。
- **B9 无持久主体 ID 与项目记忆分层铁律** ✅ — n2d 后端能力必须区分两层：① **公开服务端持久主体 ID / character subject handle**；② **项目记忆式主体连续性**。Codex/OpenAI 若当前公开能力面没有持久主体 ID，只能写「无公开服务端持久主体 ID / 未证实 subject handle」，**不得写成不能做角色一致性**，也不得因为 `persistent_subject=False` 自动阻断核心/长线角色出图。只要官方文档/本机 CLI 已证实后端能消费图片输入或高保真多图参考，适配层必须允许项目记忆路线：`identity_registry` + 共享定妆 PNG + `reference_group` + `codex_reference_bundles` / 等价 `reference_manifest` + 每镜真实图片入参（如 Codex `--image`）+ 分层/反打/单人合成 + full `image_qc`。这不是把项目记忆伪装成 subject_id；报告必须保留 `persistent_subject=False`，并把风险标为 high/需 QC。真正应阻断的是：共享定妆/脸锚仍是 `planned`、`actual image inputs=0`、`missing_ready_refs` 未清零、多人同框缺 `split_composite`/身份槽位、或 full QC 缺失/失败。未来改 skill 不得把「无持久主体 ID」重新等同于「无法锁角色」或「必须切后端」；只能用等价或更严格的真实参考图入参、manifest 和 QC 机检替换。机器覆盖：`tools/validate_skills.py --only B9` 守宪法条文、后端能力表、Codex 参考图束 runner、`face_drift_risk` 项目记忆缓解逻辑和回归测试。
- **B10 闸门克制 + 启发式不硬阻断（2026-06-26）** — 一致性/留存/叙事的**确定性闸已饱和**（`gate.py` ~94 个 `check_*`），继续堆同类闸边际收益转负，且会让闸门**互相误升级（掣肘）**。新增 BLOCK 级确定性闸**必须有证据支撑**（像素/embedding/外部基准/可复算指纹），不得再靠**关键词命中、任意数值阈值或小样本回归**这类**脆弱启发式**做硬阻断。脆弱启发式只能 ≤WARN/INFO，并在 `gate.add()` 标 `confidence="heuristic"`——该标记会把任何误声明为 BLOCK 的启发式 finding **自动降回 WARN**（防阈值沙化把低置信信号升成发布阻断）。机器覆盖：`gate.add()` 的 heuristic 降级守卫 + 回归测试；`gate_policy_coverage.gate_inventory()` 守 gate.py 无「定义在却从 `run()` 不可达」的死闸（堵 dead BLOCK 分支整类回归）。改 gate 时优先**收敛/拆分/降噪**，不优先加闸。
- **B11 load-bearing 一致性闸不准降级 + demo 不降标准铁律（2026-06-27 用户裁决）** ✅ — 为高质量出图/出视频建的**承重一致性硬闸**（崩脸/脸锚/跨集脸漂/视觉契约继承/参考规划落实/状态·语义·多模态连续性等），一经登记为 load-bearing，其 **BLOCK 强制力不得随 `consistency_release_profile`（demo/production）降级**——**demo 与 production 共享同一 enforcement floor，demo 不得为"快速小样"降低一致性标准**；也不得把已是硬闸的检查改成 opt-in/默认关而不留痕。这与 **B10 互为对偶**：B10 防**过度**阻断（脆弱启发式不许硬挡），B11 防**欠**强制（承重硬闸不许被悄悄降级）。降级一个 load-bearing 闸是**显式审计决定**，必须先改 `skills/n2d-review/scripts/consistency_charter.py` 里该闸的 `may_be_profile_gated`/`may_be_opt_in` 一行（带 `rationale`+`decided` 留痕），不得直接在 `gate.py` 把 `sev` 塞进 `if profile==production`。机器覆盖：`consistency_charter.py`（enforcement 不变量登记表，现 22 个 locked 闸）+ `test_consistency_charter.py`（introspect `gate.py` 源码：① 每个 locked 闸仍无条件 BLOCK·跟一层 severity helper；② **完整性守护 `find_unregistered_profile_gates`——任何按 profile 决定 BLOCK 的函数都必须在 charter 登记裁决，根除"修了一个漏一个"，新增 profile 门控不登记即红**）+ `gate.py` 运行时 meta-gate `_consistency_charter_issues`（闸函数失联即 BLOCK）+ `self_audit.py check_consistency_charter`。**C4 豁免也堵死（2026-06-27 裁决）**：重依赖（insightface/VLM）缺失不再是 demo 静默 WARN 免单，而是 BLOCK——唯一出口是**显式留痕 waiver**（如 `N2D_ALLOW_DEGRADED_QC=1`）；即"缺依赖必须显式自负其责"，不是默认放行（与 C4 不矛盾：C4 要求"讲清该装什么"，B11 要求"没装就别静默当通过"）。**例外**：留存/叙事节奏闸（series_retention/episode_narrative_floor/pilot_arc）是另一议题，charter 里以 `may_be_profile_gated=True + out_of_scope_retention` 显式留痕保留，不属本条一致性范围。背景：c9d37df5/8f2e4c3f 曾把脸漂总闸/参考规划闸藏在"措辞优化""记录产物"提交里降成 production-only，无任何测试变红——B11 + charter 守护把这类静默降级挡在合入前。

- **B12 上游创作合同铁律 / “好看”可签收（2026-07-01）** ◑ — n2d-script 这类位于贵工位上游的创作阶段，必须升级为**编剧室 + 导演预演 + 制片交接合同**，不是单纯“剧本/分镜生成器”。“好看”不得停留在散文评价或 prompt 形容词里，必须拆成下游可消费、可验收、可重签的结构字段：本集 `core_attraction`（观众为什么看）、`first_3s_visual_hook`（无声滑屏也能读懂的首屏钩）、`retention_promise_ledger`（承诺/悬念/兑现账本）、逐 Clip `dramatic_function`、关键镜 `audience_effect`、开放问题 `audience_question_ledger`、角色 `performance_cues`、奇观镜 `spectacle_story_function`、以及有账改编 `adaptation_triage`。image/video 等下游阶段不得只“参考”这些字段，而必须把它们写进 prompt / route /执行包，并产出 SHA 绑定的消费收据（如 `script_contract_applied_第N集.json` 的 `出图` / `出视频` scope）；gate 在 prompt 已存在时检查合同通过、收据新鲜、字段完整，缺失或过期即回到 `n2d-script` 或对应 prompt 阶段。与 B10 的边界：本条阻断的是**合同字段缺失、合同未通过、下游未消费或收据失效**这类确定性交接缺口；不允许把主观“我觉得不够好看”、关键词密度或脆弱审美阈值伪装成 BLOCK。

- **B13 完整生产合同 ≠ 后端提交 prompt（2026-07-10）** ◑ — 凡生成阶段的完整合同含路由理由、内部 ID/路径、身份/资产注册表、合规/审计说明、QC、后期说明，或目标后端有独立字段/控制输入时，必须在**本线**建立 `contract → backend-aware compiler → submit fields` 单向边界：①完整合同继续严格，供 gate、人审、溯源；②compiler 只抽取模型实际能执行的可见/可听意图，按具体模型/渠道 profile 输出主 prompt、独立负向、歌词、时长、参考图/控制输入等结构字段；③runner 只提交 compiler 产物，不得回退为整份合同拼接；④manifest 记录 compiler kind/version/profile、source hash、submit hash，正式生成前 gate/runner 校验后端一致性与 lint；⑤各线 compiler 只住本线 `_lib`，不以“通用 prompt 工具”为名建立跨线代码依赖。**领域差异必须保留**：视频通常 motion-first 精简；漫画静态图仍需画面事实/构图/画风/稿层；歌曲精简 style 但歌词原文完整进入独立 lyrics 字段；长篇文本写作所需的设定、状态、读者契约和章节上下文本身就是生成输入，不得为追求短 prompt 擅自删减，应使用逐章 task packet、static/dynamic context、检索、hash 和缓存度量分层。只有存在真实 provider 字段边界时才新增 compiler，不能为了形式统一强造一层。

## C. 选择点与适配层

- **C1 通用 skill、私有选择** — skill **不得硬编码**唯一平台/后端/分辨率/音色。凡「让用户选」的点：读 `<作品根>/_设置.md` → 否则读用户私有全局默认（如 `创作偏好-默认.md`、`.agents/创作偏好-默认.md`、`.codex/创作偏好-默认.md`，`.claude/` 仅作 legacy 兼容）并预填 + 告知一次 → 否则问一次，然后持久化沉默沿用。**例外**：除 D4 的仓库创作源文本 / 同源改编默认外，合规 / 不可逆 / 花钱的点每次都复确认。
- **C2 选择菜单 = 带日期候选快照，不是真理** ◑ — 模型/平台/法规/价格/规格等会变的信息：执行前按需用专业知识/项目 references/官方文档/实时搜索核验刷新；用户永远可手输 `自定义`/`manual`（逃生口常驻）；每份易变候选清单带 `采集日期：YYYY-MM-DD` 戳。skill **不直接依赖菜单文案**，而经本线适配层（本线 `_lib` / craft contract / backend registry / model router 等）把选择归一到能力、参数、CLI/API、降级方案和合规闸门；**适配不了就停下报缺口，不偷偷换路**。各线策略差异是故意的（如 ad 禁即梦 ≠ n2d 放行即梦官方），**分别刷新、绝不合并候选清单**。新易变清单注册到对应线 `_lib/freshness.py:CANDIDATE_SOURCES`（若该线有候选源；目前 n2d/ad 有），用同目录 `refresh.py` 刷新。**候选项「会过期」不等于「可以含糊」**：易变的是版本号，不变的是「指代必须落到具体模型」——见 **C5**。
- **C3 后端能力结论必须查证再落地** — 任何“某后端不能/能做多图、主体 ID、seed、批量、分辨率、价格/额度、合规输出”的结论都属于易变事实，不能凭模型记忆、旧项目经验或一次失败直接写死。做阻断、迁移、降级、推荐或修改 skill 前，必须先查官方文档/实时资料，再查本机 CLI/API `--help` / features / 版本，必要时跑最小 smoke test；把日期、来源、命令和结果落进 adapter 注释、manifest、进度或候选 provenance。证据不足时只允许写“当前未证实/当前 runner 未接入”，不得写“后端没有”。若查证能力存在，适配层必须把能力接成结构化、可审计入参（如 `--image` 文件、subject_id、seed 字段）并写生产事件，而不是继续把能力退化成 prompt 文本。
- **C4 主流程不绑后端、不硬依赖安装；重依赖走适配层 + 引导安装 + 优雅降级** ◑ — skill 的**主流程**不得深度绑定某个具体后端，也不得把「装了某软件 / 某 conda 环境 / 某 CLI 就绪 / 有某凭证」当作能跑下去的**硬前置**。凡需要重依赖（模型权重、conda 环境、付费 API、本机 CLI、第三方二进制）的能力，一律经**本线适配层**（`_lib` / craft contract / backend registry / model router / `*_runner.py`）接入，主流程只面向「能力 + 归一参数 + 降级方案」，不面向具体实现。依赖**缺失或未安装时必须优雅降级**：主流程仍要产出稳定、可续跑的中间物（prompt 包 / job 包 / manifest / 占位 + 合规留痕，见 B4），并向用户**指明缺什么、按哪份 `references/<...>.md` 安装**（安装说明 + 获取路径放 references，重资产装在 git 外，见 E2），**而不是直接报错中断或让整条流水线跑不起来**（跨线交接缺失同样降级，见 A1）。一句话判准：**断网、没装任何重依赖、没有任何付费凭证的纯净机器上，主流程仍应能一路产出 job 包并把"该装什么、怎么装"讲清楚**；要求安装是适配层的可选增强，绝不是主流程的入场券。

- **C5 后端指代必须落到具体模型，不写 agent / 渠道 / 厂商（铁律）** — 凡指名「由什么**生成**这张图 / 这段视频」，指代必须落到**具体模型名（含版本）**：`GPT Image 2` / `Seedream 4.5` / `Nano Banana Pro(Gemini 3 Pro Image)` / `Seedance 2.0` / `Veo 3.1`，**不得只写 agent / 渠道 / 厂商 / 产品壳**（`Codex` / `即梦` / `渠道商` / 含糊的「某后端 / 同视频AI」）。agent / 渠道 / CLI / API / 网页入口只作为**访问入口（access path）单独记录**，与模型**分列**——这已是视频侧 `生视频模型`(模型) vs `生视频渠道`(入口) 的做法，图片侧 `生图模型`(模型) vs `生图渠道`(入口) **同此对齐**（旧 `生图AI` 把壳当生成者，已纠正为以模型为准）。**与 C2 不冲突**：C2 管「版本会过期、执行前刷新、留 `自定义` 逃生口」，C5 管「**指代必须精确到模型这一层**」——两条叠加 = 模型名既**带采集日期、可刷新**，又**不准退化成渠道壳**。理由：壳是会变的（即梦今天调 Seedance 2.0、明天可能换；`codex` 实际调 `GPT Image 2`），把壳当生成者会让**能力判断 / 路由 / 记账 / 审计 / 一致性与合规结论**全部漂离真实模型；能力、价格、参考预算、主体 ID、口型、水印都挂在**模型**上，不在壳上。落地：① 选择点的「生成轴」默认值写**模型名**；② adapter / backend registry / model router / dashboard 记账以**模型为主键、渠道为副**（route 写 `model+version` + `channel/CLI` 两个字段）；③ 散文按 C2 / 模型矩阵「正文写能力」，但凡**指名具体生成者**必到模型。

- **C6 剧情 / 质量先于后端能力，不为迁就后端弱点降级创作决策** — skill 的**创作决策**（分镜要不要多人同框、近景给多大表情幅度、镜头多长、要不要某个奇观镜）由**剧情与质量目标**驱动，**不得为迁就当前某后端的短板而降级、回避或删改创作决策**。后端能力只决定**实现路径与补偿手段**（换更强模型、分别出图 + 分区合成、首尾双帧只插值、拆段接力、加参考 / 表情库 / 人审），**不决定「这个镜头能不能存在」**。与 C4 / 「标准先行」叠加：C4 = 主流程不绑后端、缺依赖优雅降级；C5 = 指代必须到模型；**C6 = 有能力时不主动把故事往后端弱点上缩**。后端在变强、会越来越强——按当下某模型的短板把故事写小，是会过期的自我设限。**边界**：本条不否定 graceful degradation（缺后端 / 缺凭证仍按 C4 产 job 包 + 指明缺口）；它针对的是「后端做得到、只是难」时**不要用回避代替攻坚**。质量硬闸（崩脸 / 串脸 / 轴线穿帮 / 音画不同步）仍是 BLOCK，但它要求的是**把难镜做对**（身份槽位 / 分区合成 / 强主体模型 / 同源首尾帧），**不是把难镜删掉**——质量门拦的是"没做对"，不是"难"。

## D. 合规硬闸门（非协商）

- **D1 授权与来源** — 声音克隆只在本人 / 已授权嗓音上做；克隆真人嗓需授权（2026 opt-in），未授权拒做。源小说/词曲默认公版 / 自有 / 已授权；本仓创作源文本和同源改编按 D4 执行。合规 / 不可逆 / 高成本的选择点即使已记录也每次复确认（见 C1 例外），D4 覆盖的原著 / 改编权不重复追问。
- **D2 各线合规策略不强行对齐** — 例如 AI 标识/水印义务在 n2d 线只作为非阻断发布待办，其他线按各自法规要求；改一条线的合规闸门不自动套到别线。
- **D3 AI 标识非阻断铁律** — n2d 的 AI 标识 / AI 披露 / 水印不得阻塞主生产流程：不得因为缺 `ai_labeling`、未落显式角标、未写元数据、未做数字水印或平台侧披露而阻断 compose/review、进度回写、dashboard 记账或后续集推进。流水线可以提供 manifest、INFO 提醒和 best-effort 后处理脚本，但失败只能形成发布前待办；若目标地区/平台要求标识，由使用方在发布工序或工具外补齐。未来改 gate、合规脚本、compose 或 review 时，只允许保持或放宽这个非阻断语义，不得把 AI 标识升级为 BLOCK。
- **D4 原著作者默认铁律** — 本仓创作线默认用户就是原著作者 / 权利人：用户直接提供的源文本、`创作区/写小说/**` 下的小说、用户在本仓创作出的词曲 / 剧本 / 分镜，以及这些作品在同项目内转 n2d / mv / ad / novel 等流水线的同源改编，默认 `status=original`，改编权默认同源自有。skill 不得因为缺外部版权证明、授权截图或额外口头确认而阻断拆集、改编、出图、出视频、合成；manifest 应自动写入等价留痕，如“仓库默认：用户为原著作者，源文本与同源改编权作者自有”。**例外**：用户明确标明第三方、转载、购买授权、公版、抓取 URL、改编他人 IP，或文本中出现明确版权冲突时，必须转入 `public_domain` / `licensed` / `stock_licensed` / `user_declared` 等对应路径并按需留 evidence/ref。D4 只覆盖原著 / 同源改编权；真人肖像、演员形象、声音克隆、第三方音乐音效字体、平台审核、广电备案、出海本地化不因“我是原著作者”而豁免。

## E. 交付约束

- **E1 交付端 VCS-free** ✅ — 交付到用户端**不能假设有 git 仓库或 git 命令**。任何 skill 不得依赖 / 探测 / 描述 git 做本仓状态、基线或变更检测（无 `git status/diff/log/rev-parse` 等）；需要变更检测时改用**内容快照**（SHA over 文件内容），不依赖 git 基线。安装类 references 可以给第三方依赖的 `git clone` 作为获取方式，但不得把本仓 workflow 的正确性建立在 git 上，并应尽量提供 release 包 / 手动下载等替代路径。
  > **历史违例已销账（2026-06）**：`skills/n2d-update` 曾用 git 基线比对，现已重构为纯内容 SHA256 快照（`build_baseline_snapshot`），并主动拒绝 legacy git 基线。`validate_skills.py` 的 `KNOWN_GIT_EXCEPTIONS` 已清空，全仓 `git` 自省调用一律 fail。
- **E2 私有配置与重资产在 git 外** — 各 AI 私有配置（`.claude/`、`.cursor/`）、大模型权重、conda 环境（`~/CosyVoice`、`~/ACE-Step` 等）不进共享 skill，按各 `references/` 安装说明本地准备。

## F. 维护与同步

- **F1 改了 skill 集合（增/删/改职责）→ 必须同步 `skills/README.md` 索引** ✅。
- **F2 改了跨线引用 / `_lib` / 调度入口 → 跑 independence audit** — `python3 tools/independence-audit/scripts/check_independence.py`，确保没误引公共层或别线代码。
- **F3 改了路由表 / 入口文档 → 三份入口保持同步** ✅ — `AGENTS.md`（工具中立）、`GEMINI.md`（per-tool 镜像）、`CLAUDE.md`（Claude Code）的关键路由入口、机检命令与约定摘要必须一致；`CLAUDE.md` 可指向 `AGENTS.md` 作为路由真值源，但不得保留过期命令或旧路径。
- **F4 实战回流铁律** — 真实作品生产是一线验证场。凡在创作、改编、分镜、配音、出图、出视频、合成、审查或批跑中暴露出可复现的 skill 缺陷，必须回流到对应 skill / `_lib` / 契约 / gate / schema / references，而不能只在单个作品目录里临时绕过。临时 workaround 只为保护当前交付，不能替代 skill 层修复；回流必须基于证据（gate 缺口、stop_reason、人工复核、batch dead letter、成本异常、用户选择摩擦、返工记录等），先保证作品可续跑，再做最小范围修正。若问题涉及题材场景、镜头契约、生成配方、产物结构或质量闸门，应补相应 fixture / golden project / 回归测试或 readiness 检查；若影响旧项目，必须提供兼容、迁移、doctor 或 n2d-update 路径。改动触及职责、路由、跨线引用或入口摘要时，按 F1/F2/F3 同步索引并跑对应机检。
- **F5 运行期自主微优化铁律** — 跑数据、批跑或真实作品生产时，agent 发现**非铁律、非合规、非高成本、非跨线架构**的小问题，可以在不中断当前交付的前提下当场做最小修复，不必等用户逐项确认。判准：只修可复现、低风险、局部、可验证的问题（脚本兼容、错误提示、日志留痕、fixture、轻量 gate 降噪、文档缺口、适配层明显 bug 等）；不得放松、绕过或重定义 B6-B11 / C1-C6 / D1-D4 里的铁律与选择点、load-bearing gate、合规授权、用户偏好、付费/联网/重依赖动作、跨线独立性、发布质量标准或 skill 职责路由。修完必须留下证据（触发条件、命令、失败到通过、测试或机检结果），并在交付说明里列明；若本线已有 friction / self_audit / 优化信号机制，不能当场修的缺陷要写入信号，能当场修的也要保留可追溯记录。影响范围不确定、会迁移旧数据、会改变成片内容或会增加成本时，先停下说明并等用户裁决。
- **F6 测试 fixture 独立于真实作品目录** ✅ — 测试可以用 `tmp_path` / `tempfile` 构造 `创作区/<线>/<测试项目>`，也可以把稳定样例放入 `tests/fixtures/**`；但不得在测试文件中硬编码引用当前仓库 `创作区/**` 下的真实作品名、绝对路径或废料/产物路径。真实作品和 `废料/` 可被清理、迁移或重跑，不能成为回归测试的隐式依赖。机器覆盖：`tools/validate_skills.py --only T1`。
- **F7 系列规模统计同步** ✅ — 改任何 `skills/<line>*` 的 `SKILL.md`、脚本、references、测试或示例文本后，必须运行 `python3 tools/update_skill_stats.py`。它会同步 `skills/README.md` 的规模表，并把 `Skill 数 | SKILL.md 总行数 | 目录文本总行数` 写入六个总领 skill（`n2d` / `novel` / `comic` / `song` / `mv` / `ad`）frontmatter 后第一行。机器覆盖：`tools/validate_skills.py --only F7`；发布/全量检查会自动发现统计过期。

---

## 不属于本宪法的（别往这塞）

- **本线特有工艺原则**留在各线 `*-craft/SKILL.md` 的 `## 设计原则`：n2d 默认原生音画 / 强控制时配音先行 + 两层出图、ad 不拆集 + cutdown 轴、song/mv 多版是默认工程事实。
- **n2d 契约层治理**（invariant vs contested、版本迁移）是运行期契约层的演进，见 `docs/n2d-原则变更提案-契约治理与一致性占位.md`，不在本跨线宪法内。
- **机器/会话事实**（哪台机器装了什么、哪个后端宕了）进 memory，不进本文件。
