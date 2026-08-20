---
name: ad
description: 拍广告 总调度 — 把【客户需求/brief】做成一条 AI 广告片（目标/KPI→创意→脚本→VO→分镜→产品/角色/场景定妆→AI出图→AI视频→剪辑交付→发布合规→质检→投放反馈）。产物落 创作区/拍广告/项目名/（成片_主片.mp4 + cutdown + 多比例）。**不拆集**、**自包含**。读 _进度.md 路由到 ad-progress / ad-update / ad-craft / ad-concept / ad-script / ad-voice / ad-image / ad-video / ad-compose / ad-review / ad-feedback。Use when given a 客户需求/brief（哪怕只有一句话）, a product/brand to advertise, an existing 拍广告 project, or asked 拍广告 / 广告创意 / TVC / 信息流广告 / 产品demo / 带货视频 / 投放复盘. Triggers 拍广告, 广告片, 广告创意, 广告脚本, 广告分镜, TVC, 信息流广告, 品牌片, 产品demo, 带货视频, 广告成片, 投放复盘, ad.
---
> 规模统计：Skill 数 14 | SKILL.md 总行数 1244 | 目录文本总行数 57286

# ad — 拍广告生产线 · 总调度

把**一份客户需求（brief）**做成一条 AI 广告片。**输入 = 客户需求/品牌产品**；**产物 = `创作区/拍广告/<项目名>/成片_主片.mp4`** + 多时长 cutdown（30→15→6s）+ 多比例（16:9/9:16/4:5/1:1）。

这条线的核心是**前端创意策划**（策略层）和**后端品牌包装/交付**：从 brief 到脚本、VO、分镜、出图、出视频、剪辑包装、cutdown 与多比例交付。

**不拆集铁律**：广告不切「集」。一条主片是一个整体（可以很长）；多时长/多比例/A·B 是**交付件 deliverable**，登记在 `_进度.md` 的「交付版本矩阵」。`ad-compose` 重剪前先用 placement adaptation 明确原生重构或经签核的机械裁切，不能把万能 reframe 当版位适配。

**自包含铁律**：`ad-*` 的创意、脚本、配音、定妆、契约继承、接缝、剪辑与交付逻辑都在广告家族内维护。

**生产数据分层**：brief、创意合同、镜头/交付矩阵、正式媒体、合规与投放反馈仍是 ad 自己的业务真值；`生产数据/artifact_catalog.json` 只是可删除、可重建的只读索引，缺失不得阻断广告流程。机器真值优先 JSON/JSONL，人读 Markdown/HTML 放 `生产数据/views/`，生成候选与缓存必须同正式交付分开。持久路径使用作品根相对路径。ad 不 import 仓库维护工具或其它系列实现，也不读取其它系列状态、缓存或业务数据。

> **发布合规是流水线内闸门**：产线不伪造平台 UI 操作，也不擅自给母版烙通用水印；但必须分别记录 AI 生成标识与商业/付费合作披露，二者不能互相替代。`campaign_readiness.json` 还要闭合落地页、offer/CTA/价格、行业×平台×辖区准入、转化事件与诊断、归因/UTM/deep-link、consent/privacy。平台动作或本地证据未完成时母版可生成，不能标记 release-ready，最终 `ad-review` 会阻断。

## 偏好（私有 · 用户选择，不写死在本 skill）

按 `../skills/ad/ad-craft/references/选择点与偏好.md` 读用户私有选择：先读 `<作品根>/_设置.md`；缺则用全局默认 `创作偏好-默认.md` 预填并告知一句；再缺则**首次问一次**→写回 `_设置.md`→同项目沉默沿用。合规/不可逆/花钱多的点（`广告法地区`、`音乐来源`、出图/出视频/合成）每次仍确认。

涉及选择点：`广告类型`、`创意路线`、`基础视觉风格`、`主片时长`、`交付比例`、`cutdown版本`、`生图模型`、`生图渠道`、`一致性增强`、`生视频模型`、`生视频渠道`、`视频模型路由`、`出视频规格`、`视频分辨率`、`配音后端`、`音乐来源`、`品牌包装模板`、`字幕语言`、`AI视觉使用披露`、`广告法地区`、`交付规格`、`生成粒度`、`目标平台`、`发行地区`。模型是具体版本，渠道只是 CLI/API/网页入口；旧 `生图AI` 不再作为正式选择点。

> 作为生产线入口：开新项目（`创作区/拍广告/<项目名>/`）时先问广告首跑选择点（如 `创意路线`、`基础视觉风格`、交付比例/时长/可用账号约束），再运行 `python3 skills/ad/scripts/init_project.py "创作区/拍广告/<项目名>" --brand <品牌>` 初始化 `_设置.md`/`_进度.md`/`需求/brief.json`。视频阶段默认 `视频模型路由=自动按镜头路由`，不在立项时强问具体 `生视频模型` / `生视频渠道`；只有客户/投放/账号要求固定后端、用户本轮已明确模型渠道、或 router/probe 找不到可执行后端时，才传 `--video-model` / `--video-channel` 覆盖落档。旧 `--video-backend` / `生视频AI` 兼容。立项同时写作品卡片字段 `_meta.json.synopsis`（先用默认广告目标占位，brief 产出后 `meta_card.py synopsis` 回填 `key_message`）与 `_meta.json.cover`（默认 `null`，`ad-image` 出竖版封面 PNG 后 `meta_card.py cover` 回填）。

## 作品根约定（不拆集）

```
创作区/拍广告/<项目名>/
├── _进度.md / _meta.json / _设置.md
├── 需求/brief.md + brief.json   客户需求结构化（品牌/产品/USP/受众/调性/强制项logo·slogan·法律声明/交付规格）
├── 创意/concept.json + concept.md + 创意脚本.md  JSON 为 big idea / 主张 / mood&reference / KV 机器真值
├── 脚本/                        广告脚本.md + voiceover.txt + 时间轴.json + storyboard.json + 字幕 + 镜头时长 + 广告法机检报告
├── 设定库/                      global_style + 角色卡 + 场景卡 + 产品卡 + voicemap.json
├── 配音/                        line_NN.wav + vo.wav + 时长清单.json + voice_qc.json
├── 出图/共享/ 出图/分镜/         三层定妆库（角色/场景/产品）+ 逐镜首尾帧 + 逐 job 生成/人审哈希收据
├── 出视频/分镜/                 每 Clip MP4 + video_model_routes.json + video_qc.json
├── 生产数据/                    producer/platform/render profile + placement adaptation + campaign readiness + dependency receipts + final frames/contact sheets + stage acceptance
├── 合成/                        成片/cutdown/多比例 + delivery/color/rendered-text/ASR/accessibility QC
├── 合规/                        locale matrix + AI usage + provenance + release variants + compliance + M0 + human signoff
├── 投放反馈/                    experiment_plan/validation + raw/ + feedback_report
└── 成片_主片.mp4
```

## 阶段 + 路由

| 阶段 | skill | 产物 | 状态 |
|---|---|---|---|
| 共享契约/立项 | 本调度 + **`ad-craft`** | `_设置.md`+`_进度.md`+`_meta.json`+`需求/brief.json`+`生产数据/producer_pack.json`+`platform_pack.json` | ✅ |
| 客户需求 brief | 本调度 | `需求/brief.md`+`brief.json`（结构化客户需求） | ✅ |
| 创意策划 | **`ad-concept`** | `创意/concept.json`（机器真值）+`concept.md`+`创意脚本.md` | ✅ |
| 广告脚本+VO+时间轴 | **`ad-script`** | `脚本/广告脚本.md`+`voiceover.txt`+`时间轴.json`+**广告法机检** | ✅ |
| VO配音 | **`ad-voice`** | `配音/时长清单.json` + `voice_qc.json`（驱动镜头时长且实测非静音/时长） | ✅ |
| 分镜（实测时长） | **`ad-script`** | `storyboard.json`+`镜头时长.json`+字幕 | ✅ |
| 投放前评分(横切·出图前) | **`ad-score`** | `评分/ad_score.json`：钩子/卖点/CTA/品牌露出/广告法/时长 → 三档 go/revise/reject + 回流清单 | ✅ |
| 三层定妆库+出图 | **`ad-image`** | 角色/场景/**产品**定妆 + 逐镜首尾帧 PNG + 每张图的提交/输出/参考/QC/具名人审哈希收据 | ✅ |
| 图生视频 | **`ad-video`** | Clip MP4 + 契约继承机检 + 模型路由 + 统一 render profile + requested↔observed 媒体收据 + video_qc | ✅ |
| 剪辑包装+交付 | **`ad-compose`** | placement adaptation 明确的原生版本/受控裁切 + actual-mode execution receipt + 原子 cutdown + 技术/色彩/最终文字/ASR/无障碍/实际 provenance QC | ✅ |
| 发布合规+投放就绪 | **`ad-craft`** | locale + 逐交付链 + 独立 AI label/商业披露收据 + campaign readiness + compliance | ✅ |
| 质检/自审(横切) | **`ad-review`** | 最终 clip/交付件首中尾帧、逐资产 contact sheet + M0 + 具名逐项哈希签收 | ✅ |
| 投放反馈(可选) | **`ad-feedback`** | 预注册单变量实验 + 平台 CSV/JSONL → 有统计边界的 Test→Learn→Refresh 报告 | ✅ |

| 用户输入 | 路由到 |
|---|---|
| 有客户需求/品牌产品，要立项拍广告（**一句话需求也行**） | 本调度 `init_project.py` 建 `创作区/拍广告/<项目>/`，把已知信息填进 `brief.json`；缺的交给 `ad-concept` 第0步访谈补齐，**不要求用户先填全 brief** |
| 要做创意/big idea/创意脚本 | `ad-concept` |
| 要写广告脚本/分镜/查广告法违禁词 | `ad-script`（配音前=脚本 pass，配音后=分镜 pass）|
| 要配 VO/旁白 | `ad-voice` |
| 要出定妆/产品图/分镜图 | `ad-image`（三层定妆库：角色/场景/产品）|
| 要图生视频 | `ad-video` |
| 出图前想评估广告值不值得做/打分 | `ad-score`（目标化 pre-spend 诊断；低分建议回流，只有广告法 block 硬挡）|
| 素材齐了要剪辑包装/出 cutdown/多比例/交付 | `ad-compose` |
| 已投放，要复盘 CTR/CVR/CPA/ROAS、A/B 或疲劳 | `ad-feedback` |
| 给了 `创作区/拍广告/<项目>/` 没说动作 / 问进度或下一步 | `ad-progress`（只读扫描 `_进度.md`，报进度 + 建议下一步） |
| 问 skill 更新是否影响本广告 / 要返工计划 / 重审重评前先看范围 | `ad-update`（只写更新影响计划和基线，不改 brief/素材/进度） |

> 推荐顺序：**目标/KPI/发行辖区 brief → ad-concept 的 `concept.json` → ad-script → ad-voice + voice_qc → 配音后分镜（claim 呈现）→ producer/platform pack + render profile → ad-score → ad-image 逐图收据 → ad-video + video_qc → placement adaptation → ad-compose 的 delivery/color/rendered-text/ASR/accessibility/provenance QC → locale + release variant（AI 标识与商业披露双收据）+ campaign readiness + compliance → 最终媒体 contact sheet + M0 + 具名人审签收 → 带功效/停止规则的实验预注册 → ad-feedback**。每阶段由 typed acceptance + 依赖哈希收据验收，不能手填假 ✅。
> **音频先行**：VO 实测时长驱动镜头时长，`ad-script` 跑两遍（脚本→配音后分镜）。广告常是「音乐床 + VO」混合驱动，音乐床作节奏锚一并记录。
> **立项完成判据**：`brief.json` 的 brand/product/usp/audience/**campaign_objective** 齐全；花钱 gate 前还必须补 claims 结构化证据、rights、legal_lines、primary_kpi 和 conversion_event。
> **零成本 demo 通道**（一句话用户的推荐路径）：进花钱 gate（出图）之前全程免费——brief 访谈 → ad-concept 创意 → ad-script 脚本(机检) → `ad-voice --backend say|estimate` 占位配音 → ad-script 分镜 storyboard。先看到完整镜头设计再决定是否花钱出图/出视频；占位配音正式定稿前须真 VO 复跑。

## 广告专有强化点

- **客户需求 brief 是 source**：除品牌/产品/USP，还必须定义广告目标、漏斗阶段、主 KPI、转化事件、offer/landing page；不再用同一评分口径服务所有目标。
- **制片前控包**：付费生产前按 claim 类型核对来源、资质、方法、条件、样本、范围、有效期、披露文案与授权；不能“先射箭后画靶”。
- **平台交付包**：平台名不等于版位。按实际 placement 的比例、时长、声音模式与安全区出包；不用“通用 9:16”伪装已适配。
- **创意策划层**：big idea / 一句话主张 / mood&reference / KV 方向（`ad-concept`）。
- **《广告法》分层机检**：法定明确禁用/失效背书、医疗疗效、虚假收益等高确定性项 block；「最新/领先/销量第一」等语境型表述 warn 并要求比较范围、时间、样本、出处和具名复核，避免关键词表代替法律判断。
- **产品定妆（三层定妆库第三层）**：hero product 包装/logo/品牌色跨镜零漂移，是最严格的"角色"。事前有 `ad-image/scripts/reference_planner.py` 按镜头变化量×后端能力开参考处方（能力表 `skills/ad/_lib/image_backend_adapter.py`，与 `一致性增强` 四档对齐），事后有 `ad-review/scripts/asset_drift_report.py` 出逐资产×逐镜时间线与 `first_bad_shot`。
- **创意承诺要兑现**：`创意/concept.json` 是创意机器真值；`ad-script/scripts/idea_payoff_ledger.py` 对账 big idea/主张/USP/KV 是否真的落镜，抓"分镜冒出 concept 未登记的卖点"这类创意漂移。单一主张聚焦(SMP)看 `usps[].supports_key_message`——拦的是卖点与主张**不相关**，不是卖点多。
- **镜头别重复单调**：一致性套件保的是"资产不漂"，`ad-script/scripts/shot_variety_audit.py` 补的是**视觉不重复**——出图前查同景别机位反复/画面描述复读/长片单场景单景别。广告有意重复（产品 beauty/片尾板/logo·CTA 板）已豁免，短广告单场景合法只 info。全 advisory，出图 gate 抬进报告不硬挡。
- **传统结构纪律机检化**：`ad-script/scripts/beat_structure_audit.py`（3s 钩子窗/品牌 5s 进场/CTA 收尾/痛点→方案顺序/ASL 带宽/字卡停留公式/静音可懂/6s 单 idea + Google ABCD 合成分）+ `see_say_audit.py`（DRTV 声画对位：VO 可演示卖点画面须看得见）。全 advisory，同 creative_axis 接法。
- **打样再放量（传统 PPM「先看小样再开机」）**：全量出图前 `ad-image/scripts/pilot_matrix.py` 从分镜挑 2-5 镜代表样（首镜/产品 hero/最高风险镜/文字板/多主体，风险镜取 `ad_reference_plan` 的 delta_score 最大者）先出先审，画风/产品还原/文字渲染塌在打样里改是小钱。advisory 计划，打不打由人定。
- **机检不许空转、硬闸不许降档**：`ad-review/scripts/verifier_coverage.py` 是覆盖账本（fail-closed）——逐机检算 适用×真跑×新鲜×检了真实对象，"registry 登记了产品而 product_qc 检了 0 张产品图"这类空转在 compose（交付点）硬挡，唯一出口 `合规/degraded_qc_waiver.json` 签核留痕；`ad-craft/scripts/consistency_charter.py` 是防降级宪章——每条承重硬闸占一行，守卫测试内省 gate.py 源码，静默降档立即红灯。
- **品牌包装 + 交付**：片尾、claim/披露原子 cutdown、placement-native 原生重剪/重做或受控裁切、统一 render profile、BT.709、响度、字幕与闪烁快筛。
- **最终文件证据**：关键口播四路对账、最终像素文字逐项具名确认、实际 C2PA/隐式标识探测、逐资产 contact sheet、逐 deliverable 发布变体链和内容哈希选择性失效。

## 合法性
- 广告 claim 须有事前合理依据；检测/统计/文献/比较引证还须清楚呈现来源、条件、适用范围/有效期。绝对化用语机检不替代这些证据。
- 代言人肖像/真人声音/授权音乐/商业字体需可追溯授权；未授权不投放。AI 生成合成内容需保留元数据、声明/标识责任与平台回执；平台侧动作由发布者执行，证据必须回写产线。

## 持续改进
工艺/翻车 → 写进对应 ad-* skill 的 `references/`。**新增/改 ad-* skill 后同步更新 `skills/README.md` + `AGENTS.md`/`GEMINI.md` 路由表 + `skills/ad/ad-craft/references/选择点与偏好.md` 选择点目录。**

## 常见错误

| 错误 | 纠正 |
|---|---|
| 把广告拆成「集」 | 不拆集；多时长/多比例走 cutdown 交付件矩阵 |
| 把所有“最/第一”一律当违法或一律放行 | 国家级/最高级/最佳等明确项硬挡；最新/领先/销量第一等先警告、补时空范围与证据并具名复核 |
| 产品包装/logo 跨镜漂移 | 产品定妆当最严格"角色"，进三层定妆库 + 逐镜锁 PROD_xx；出图前跑 `reference_planner`（产品镜单参考最危险），审片跑 `asset_drift_report` 看从第几镜开始崩 |
| 定妆母本改了却没刷出图快照 | `设定库/asset_registry.json` 是母本、`出图/共享/` 是快照；母本改了要重跑 `plan_prompts.py` 刷新，否则 prompt/QC 照过期 registry 跑（gate 已硬挡 `asset_registry_snapshot_stale`）|
| 创意定完 big idea 就没人管 | `创意/concept.json` 落机器真值，`idea_payoff_ledger` 对账兑现；分镜临时加卖点会被 `usp_offledger` 抓 |
| App/UI/片尾镜没写 `PROD_*`/`BRAND_*` | producer_pack 和 product_qc 会抓；先把产品/App/品牌资产结构化绑定再出图 |
| 跳过创意策划直接出图 | 先 `ad-concept` 定 big idea/主张，再脚本分镜，别无脑批量生成 |
| 不留授权痕/平台声明证据 | 先写 ai_usage，再分别补 AI label 与商业/付费合作披露收据，并跑 campaign readiness + compliance；平台动作由发布方执行，证据必须回写后才可 release-ready |
| 只写平台名或“海外”就开投 | 补实际 placement 模板和逐 jurisdiction 法务复核；复核须绑定当前 release content SHA |
| 用旧 `生图AI=Codex/厂商名` | 改为具体 `生图模型` + 独立 `生图渠道`；落图 job 两字段都要留 provenance |
| 旧项目沿用历史 ✅ | 先用 `ad-craft/scripts/migrate_project.py` dry-run，再 `--write`；旧状态按新验收/哈希收据重算，pending 不得伪造 |
