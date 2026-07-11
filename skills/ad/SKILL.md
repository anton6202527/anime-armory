---
name: ad
description: 拍广告 总调度 — 把【客户需求/brief】做成一条 AI 广告片（目标/KPI→创意→脚本→VO→分镜→产品/角色/场景定妆→AI出图→AI视频→剪辑交付→发布合规→质检→投放反馈）。产物落 创作区/拍广告/项目名/（成片_主片.mp4 + cutdown + 多比例）。**不拆集**、**自包含**。读 _进度.md 路由到 ad-progress / ad-update / ad-craft / ad-concept / ad-script / ad-voice / ad-image / ad-video / ad-compose / ad-review / ad-feedback。Use when given a 客户需求/brief（哪怕只有一句话）, a product/brand to advertise, an existing 拍广告 project, or asked 拍广告 / 广告创意 / TVC / 信息流广告 / 产品demo / 带货视频 / 投放复盘. Triggers 拍广告, 广告片, 广告创意, 广告脚本, 广告分镜, TVC, 信息流广告, 品牌片, 产品demo, 带货视频, 广告成片, 投放复盘, ad.
---
> 规模统计：Skill 数 14 | SKILL.md 总行数 900 | 目录文本总行数 19828

# ad — 拍广告生产线 · 总调度

把**一份客户需求（brief）**做成一条 AI 广告片。**输入 = 客户需求/品牌产品**；**产物 = `创作区/拍广告/<项目名>/成片_主片.mp4`** + 多时长 cutdown（30→15→6s）+ 多比例（16:9/9:16/1:1）。

这条线的核心是**前端创意策划**（策略层）和**后端品牌包装/交付**：从 brief 到脚本、VO、分镜、出图、出视频、剪辑包装、cutdown 与多比例交付。

**不拆集铁律**：广告不切「集」。一条主片是一个整体（可以很长）；多时长/多比例/A·B 是**交付件 deliverable**，登记在 `_进度.md` 的「交付版本矩阵」，由 `ad-compose` 重剪/reframe。

**自包含铁律**：`ad-*` 的创意、脚本、配音、定妆、契约继承、接缝、剪辑与交付逻辑都在广告家族内维护。

> **发布合规是流水线内闸门**：产线不伪造平台 UI 操作，也不擅自给母版烙通用水印；但必须用 `ai_usage.json` + `compliance_manifest.json` 记录 AI 使用、显式/隐式标识责任、平台主动声明和证据。平台声明尚未完成时母版可生成，不能标记 release-ready，最终 `ad-review` 会阻断。

## 偏好（私有 · 用户选择，不写死在本 skill）

按 `../skills/ad-craft/references/选择点与偏好.md` 读用户私有选择：先读 `<作品根>/_设置.md`；缺则用全局默认 `创作偏好-默认.md` 预填并告知一句；再缺则**首次问一次**→写回 `_设置.md`→同项目沉默沿用。合规/不可逆/花钱多的点（`广告法地区`、`音乐来源`、出图/出视频/合成）每次仍确认。

涉及选择点：`广告类型`、`创意路线`、`基础视觉风格`、`主片时长`、`交付比例`、`cutdown版本`、`生图AI`、`一致性增强`、`生视频模型`、`生视频渠道`、`视频模型路由`、`出视频规格`、`视频分辨率`、`配音后端`、`音乐来源`、`品牌包装模板`、`字幕语言`、`AI视觉使用披露`、`广告法地区`、`交付规格`、`生成粒度`、`目标平台`、`发行地区`。

> 作为生产线入口：开新项目（`创作区/拍广告/<项目名>/`）时先问广告首跑选择点（如 `创意路线`、`基础视觉风格`、交付比例/时长/可用账号约束），再运行 `python3 skills/ad/scripts/init_project.py "创作区/拍广告/<项目名>" --brand <品牌>` 初始化 `_设置.md`/`_进度.md`/`需求/brief.json`。视频阶段默认 `视频模型路由=自动按镜头路由`，不在立项时强问具体 `生视频模型` / `生视频渠道`；只有客户/投放/账号要求固定后端、用户本轮已明确模型渠道、或 router/probe 找不到可执行后端时，才传 `--video-model` / `--video-channel` 覆盖落档。旧 `--video-backend` / `生视频AI` 兼容。

## 作品根约定（不拆集）

```
创作区/拍广告/<项目名>/
├── _进度.md / _meta.json / _设置.md
├── 需求/brief.md + brief.json   客户需求结构化（品牌/产品/USP/受众/调性/强制项logo·slogan·法律声明/交付规格）
├── 创意/concept.md + 创意脚本.md  big idea / 主张 / mood&reference / KV方向
├── 脚本/                        广告脚本.md + voiceover.txt + 时间轴.json + storyboard.json + 字幕 + 镜头时长 + 广告法机检报告
├── 设定库/                      global_style + 角色卡 + 场景卡 + 产品卡 + voicemap.json
├── 配音/                        line_NN.wav + vo.wav + 时长清单.json
├── 出图/共享/ 出图/分镜/         三层定妆库（角色/场景/产品）+ 逐镜首尾帧
├── 出视频/分镜/                 每 Clip MP4 + video_model_routes.json + video_qc.json
├── 生产数据/                    producer_pack.json + platform_pack.json + consistency_findings.json
├── 合成/                        成片_主片.mp4 + cutdown/ + 多比例/
├── 合规/                        ai_usage.json + AI使用说明.md + compliance_manifest.json
└── 成片_主片.mp4
```

## 阶段 + 路由

| 阶段 | skill | 产物 | 状态 |
|---|---|---|---|
| 共享契约/立项 | 本调度 + **`ad-craft`** | `_设置.md`+`_进度.md`+`_meta.json`+`需求/brief.json`+`生产数据/producer_pack.json`+`platform_pack.json` | ✅ |
| 客户需求 brief | 本调度 | `需求/brief.md`+`brief.json`（结构化客户需求） | ✅ |
| 创意策划 | **`ad-concept`** | `创意/concept.md`+`创意脚本.md` | ✅ |
| 广告脚本+VO+时间轴 | **`ad-script`** | `脚本/广告脚本.md`+`voiceover.txt`+`时间轴.json`+**广告法机检** | ✅ |
| VO配音 | **`ad-voice`** | `配音/时长清单.json`（驱动镜头时长） | ✅ |
| 分镜（实测时长） | **`ad-script`** | `storyboard.json`+`镜头时长.json`+字幕 | ✅ |
| 投放前评分(横切·出图前) | **`ad-score`** | `评分/ad_score.json`：钩子/卖点/CTA/品牌露出/广告法/时长 → 三档 go/revise/reject + 回流清单 | ✅ |
| 三层定妆库+出图 | **`ad-image`** | 角色/场景/**产品**定妆 + 逐镜首尾帧 PNG | ✅ |
| 图生视频 | **`ad-video`** | Clip MP4 + 契约继承机检 + 模型路由 + video_qc | ✅ |
| 剪辑包装+交付 | **`ad-compose`** | 成片 + 品牌包装 end card + cutdown + 多比例 + 交付规格 | ✅ |
| AI披露/发布合规 | **`ad-craft`** | `ai_usage.json` + `compliance_manifest.json`（平台声明证据/标识责任/元数据） | ✅ |
| 质检/自审(横切) | **`ad-review`** | 一致性 findings + 成片/广告法/video_qc/delivery_qc/发布合规证据 + 人工签收 | ✅ |
| 投放反馈(可选) | **`ad-feedback`** | 平台 CSV/JSONL → 有样本门槛和区间的 Test→Learn→Refresh 报告 | ✅ |

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

> 推荐顺序：**目标/KPI brief → ad-concept → ad-script → ad-voice → 配音后分镜 → producer_pack + platform_pack → ad-score（启发式建议；广告法仍硬挡）→ ad-image → ad-video + 实测 video_qc → ad-compose + delivery_qc → AI/发布合规 manifest → ad-review → ad-feedback（投放后）**。
> **音频先行**：VO 实测时长驱动镜头时长，`ad-script` 跑两遍（脚本→配音后分镜）。广告常是「音乐床 + VO」混合驱动，音乐床作节奏锚一并记录。
> **立项完成判据**：`brief.json` 的 brand/product/usp/audience/**campaign_objective** 齐全；花钱 gate 前还必须补 claims 结构化证据、rights、legal_lines、primary_kpi 和 conversion_event。
> **零成本 demo 通道**（一句话用户的推荐路径）：进花钱 gate（出图）之前全程免费——brief 访谈 → ad-concept 创意 → ad-script 脚本(机检) → `ad-voice --backend say|estimate` 占位配音 → ad-script 分镜 storyboard。先看到完整镜头设计再决定是否花钱出图/出视频；占位配音正式定稿前须真 VO 复跑。

## 广告专有强化点

- **客户需求 brief 是 source**：除品牌/产品/USP，还必须定义广告目标、漏斗阶段、主 KPI、转化事件、offer/landing page；不再用同一评分口径服务所有目标。
- **制片前控包**：付费生产前跑 `ad-craft/scripts/producer_pack.py`，把传统广告的 PPM/producer packet 落成 `生产数据/producer_pack.json/md`：shot list、rights/claims/legal、交付矩阵、`PROD_*`/`BRAND_*` 资产绑定、审批阻断项一处对账。
- **平台交付包**：按 placement/overlay-aware 安全区出包；未知平台无当前规格就 block，不用“通用 9:16”伪装已适配。
- **创意策划层**：big idea / 一句话主张 / mood&reference / KV 方向（`ad-concept`）。
- **《广告法》违禁词机检（硬闸门）**：绝对化用语「最/第一/国家级」、虚假宣传、医疗保健极限词 → `ad-script/ad_law_check.py` 命中即 block。
- **产品定妆（三层定妆库第三层）**：hero product 包装/logo/品牌色跨镜零漂移，是最严格的"角色"。
- **品牌包装 + 交付**：片尾 end card（logo+slogan+CTA）、cutdown 多时长、多比例 reframe、交付规格（响度 LUFS/安全框）。

## 合法性
- 广告 claim（功效/对比/数据）须有依据；绝对化用语等违禁词由 `ad-script` 机检拦截。
- 代言人肖像/真人声音/授权音乐/商业字体需可追溯授权；未授权不投放。AI 生成合成内容需保留元数据、声明/标识责任与平台回执；平台侧动作由发布者执行，证据必须回写产线。

## 持续改进
工艺/翻车 → 写进对应 ad-* skill 的 `references/`。**新增/改 ad-* skill 后同步更新 `skills/README.md` + `AGENTS.md`/`GEMINI.md` 路由表 + `skills/ad-craft/references/选择点与偏好.md` 选择点目录。**

## 常见错误

| 错误 | 纠正 |
|---|---|
| 把广告拆成「集」 | 不拆集；多时长/多比例走 cutdown 交付件矩阵 |
| 脚本写绝对化用语「最/第一/国家级」 | `ad-script` 广告法机检会 block；改合规表述并留 claim 依据 |
| 产品包装/logo 跨镜漂移 | 产品定妆当最严格"角色"，进三层定妆库 + 逐镜锁 PROD_xx |
| App/UI/片尾镜没写 `PROD_*`/`BRAND_*` | producer_pack 和 product_qc 会抓；先把产品/App/品牌资产结构化绑定再出图 |
| 跳过创意策划直接出图 | 先 `ad-concept` 定 big idea/主张，再脚本分镜，别无脑批量生成 |
| 不留授权痕/平台声明证据 | 先写 ai_usage，再写 compliance_manifest；平台动作由发布方执行，证据必须回写后才可 release-ready |
