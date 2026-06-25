# Skill 设计原则（设计宪法）

> **这是本仓库唯一的「怎么*建造* skill」权威法条**（authoring-time constitution）。
> 跨工具、随仓库交付、对所有四条线（n2d / song / mv / ad）生效。
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

- **A1 四线自包含、可单独分发** ✅ — 每条线本线脚本只 import 本线 `_lib`/craft 工具，**不依赖 `skills/common/`**（已删），**不 import 别线实现**。novel 与 n2d 之间必须零交接、零数据耦合；其它跨线交付只能是用户显式选择的成品文件交接，交接缺失必须**优雅降级**，不能让本线主流程跑不起来。**独立性延伸到散文**：`skills/<line>/**.md` 不得提别线名/别线根标签/别线 skill —— 这条 strict-docs 门已是 `check_independence.py` 的**默认行为**（`--lenient-docs` 仅在确有需要时降级为只查代码级耦合）。机检：`tools/independence-audit/scripts/check_independence.py`，novel/n2d 另跑 `tools/independence-audit/scripts/check_novel_n2d_zero_coupling.py`。
- **A2 仓库级 meta 工具放 `tools/`，不放 `skills/`** — 不是某条创作线能力的单副本维护工具（independence-audit、shared-cleanup、validate_skills、打包/发布脚本等）留 `tools/` 或独立单副本，不混进 `skills/` 的创作线命名空间。**例外**：属于某条线用户工作流的一线能力（如 `n2d-progress`）仍是该线 skill，可以留在 `skills/`。
- **A3 `skills/` 扁平、按名字前缀分组** — `n2d-*` / `song-*` 等。SKILL.md frontmatter `description` + 正文 `Triggers`/`Use when` **就是路由依据**，匹配用户意图，不另建路由表逻辑。

## B. Skill 编写法

- **B1 脚本通用、无专有 API** — 纯 Python / bash，只调通用工具（`ffmpeg`/`librosa`/`whisper`/`yt-dlp`/生图生视频 CLI）；不绑定任何一家 AI 的专有 SDK；引用路径用中立的 `skills/...`。
- **B2 推荐 skill 一律写裸名** ✅ — 输出「下一步」或推荐调用时写 `n2d-image`，**不写** `/n2d-image`（有些 agent 把 `/...` 当内置斜杠命令报错）。
- **B3 prompt / 产物分离** — prompt 包与生成产物分目录、分文件，不混写。
- **B4 脚本不伪装云端自动化** — 没有凭证/后端 SDK 时，只产稳定 prompt/job 包 + 合规留痕；真正调用 Suno/即梦/Kling 等交对应后端工具，外部生成后再登记。
- **B5 阶段完成即回写 `_进度.md`** — 用确定性脚本（`progress_set.py` / `update_progress_stage()`）回写，不只在文档里说「更新进度」。正式产物阶段默认先过 `gate.py`。
- **B6 高风险连续性铁律必须机器化** ◑ — 跨阶段/跨帧/高成本的身份、资产、合规、成本规则不得只写在 SKILL.md 里靠人记；必须有确定性 gate、生产入口 guard 或回归测试覆盖，且正式产物入口不能提供无保护绕过。**n2d 图生视频非协商例**：同一角色多关键帧 Clip 的首/中/尾锚图必须来自同一个 `identity_registry` 角色/形态和同一套可执行 `reference_group`，prompt 必须绑定 `CHAR_xx/形态`、`reference_group=<同源组>`、脸型/眼距/鼻梁/下颌/发型发髻/标志配饰/服装配色等身份不变量；大表情近景必须使用同源 `reference_group.expressions` 或表情定妆首尾双帧，并写 `表情锚`、`表情幅度`、`锁脸不锁情`。后端支持 Character ID / Face Lock / reference controls / LoRA 时必须同时传原生身份；不支持时只能转入**保真实现分解**（降低运动幅度、缩小景别、侧脸/手部/反应镜、拆 Clip、分区构建等），但不得删戏、砍人物、改变动作目标或弱化剧情/情绪功能。未来改 skill 不得删除、绕过或弱化这类铁律；若确需重构，只能用等价或更严格的确定性机检 + 回归测试替换。
- **B7 人物定妆基础包不可缺失铁律** ✅ — n2d 中任何会入镜的人物、角色形态、服装/觉醒/妖形变体，只要不是明示 `restricted_partial` 且永不露完整脸的局部参考，都必须先具备**七类基础定妆包**：① 正面主参考 `front`；② 45°/三分之二侧脸 `three_quarter`；③ 侧面 `side`；④ 背面 `back`；⑤ 半身或全身服装体态 `half_body`/`full_body`；⑥ 同源脸部特写或基础表情脸锚 `face_anchor_refs`/`expressions`；⑦ 三视图/设定表人审拼版 `turnaround`。**三视图不能替代拆分 PNG**，且拆分 PNG 也不能逐张重生：45°/侧/背必须从同一张人审通过 turnaround 同源母本派生，半身/脸部特写必须从已通过正面裁切，`ready` 必须登记 `derivation.method/source_path/source_sha256/crop_box`。`planned` 只能表示待补缺口，不能放行；主角、配角、功能角色、路人和一次性人物同一基础门槛，角色体量只影响表情库、动作参考、主体库/LoRA 是否升档。机器覆盖：`n2d-image/scripts/derive_makeup_pack.py` 同源派生、`n2d-review/scripts/gate.py` 的 `check_identity_registry` 与回归测试，`tools/validate_skills.py --only B7` 防止宪法、n2d-image 铁律、gate 常量或测试被删弱。
- **B8 分集叙事连续性铁律** ◑ — 凡做拆集、分集、分段剧本的 skill，**不得设置单集时长硬性上限或下限**，也不得为了凑时长/字数把一场戏、一个爽点或一个 cliffhanger 劈断。时长只能是软节奏意图、容量估算或统计 WARN；最终边界必须优先服从剧情连贯性与完整闭环。每集至少完成 **冲突 → 爽点/反转 → 钩子** 的戏剧闭环，允许短集或长集，只要闭环成立且下一集能冷开场。粗拆脚本只能产脚手架，正式写词前必须用确定性边界预筛或等价 guard 把「章内续切、弱钩、半句、纯过渡、短/长但无闭环」标出；高风险窗口未写边界复核记录时，不得进入正式 voiceover/分镜定稿。
- **B9 无持久主体 ID 与项目记忆分层铁律** ✅ — n2d 后端能力必须区分两层：① **公开服务端持久主体 ID / character subject handle**；② **项目记忆式主体连续性**。Codex/OpenAI 若当前公开能力面没有持久主体 ID，只能写「无公开服务端持久主体 ID / 未证实 subject handle」，**不得写成不能做角色一致性**，也不得因为 `persistent_subject=False` 自动阻断核心/长线角色出图。只要官方文档/本机 CLI 已证实后端能消费图片输入或高保真多图参考，适配层必须允许项目记忆路线：`identity_registry` + 共享定妆 PNG + `reference_group` + `codex_reference_bundles` / 等价 `reference_manifest` + 每镜真实图片入参（如 Codex `--image`）+ 分层/反打/单人合成 + full `image_qc`。这不是把项目记忆伪装成 subject_id；报告必须保留 `persistent_subject=False`，并把风险标为 high/需 QC。真正应阻断的是：共享定妆/脸锚仍是 `planned`、`actual image inputs=0`、`missing_ready_refs` 未清零、多人同框缺 `split_composite`/身份槽位、或 full QC 缺失/失败。未来改 skill 不得把「无持久主体 ID」重新等同于「无法锁角色」或「必须切后端」；只能用等价或更严格的真实参考图入参、manifest 和 QC 机检替换。机器覆盖：`tools/validate_skills.py --only B9` 守宪法条文、后端能力表、Codex 参考图束 runner、`face_drift_risk` 项目记忆缓解逻辑和回归测试。

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

---

## 不属于本宪法的（别往这塞）

- **本线特有工艺原则**留在各线 `*-craft/SKILL.md` 的 `## 设计原则`：n2d 默认原生音画 / 强控制时配音先行 + 两层出图、ad 不拆集 + cutdown 轴、song/mv 多版是默认工程事实。
- **n2d 契约层治理**（invariant vs contested、版本迁移）是运行期契约层的演进，见 `docs/n2d-原则变更提案-契约治理与一致性占位.md`，不在本跨线宪法内。
- **机器/会话事实**（哪台机器装了什么、哪个后端宕了）进 memory，不进本文件。
