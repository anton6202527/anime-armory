# ad-* 机器契约（人读版）

机器字段以 `scripts/contract.py` 为准。拍广告线**自包含**：字段、阶段、选择点和交付矩阵都在本系列独立维护。

## 作品根（不拆集）

```text
创作区/拍广告/<项目名>/
├── _设置.md / _meta.json / _进度.md
├── 需求/
│   ├── brief.md            客户需求（人读）
│   └── brief.json          客户需求（结构化：品牌/产品/USP/受众/调性/强制项/交付规格）
├── 生产数据/
│   ├── producer_pack.json   制片前控包（PPM/producer packet 机器版）
│   ├── producer_pack.md     制片前控包（人读审批版）
│   ├── platform_pack.json   平台+实际 placement 交付包（安全区/分辨率/时长/cutdown矩阵）
│   ├── artifact_dependency_graph.json + dependency_receipts.json
│   ├── final_media_consistency.json + final_media_frames/ + final_media_contact_sheets/
│   └── stage_acceptance/    每阶段统一验收报告；完成状态的证据
├── 创意/
│   ├── concept.md          big idea / 主张 / mood&reference / KV方向
│   └── 创意脚本.md          creative treatment（故事线/节奏）
├── 脚本/
│   ├── 广告脚本.md          画面+台词+VO+秒级时间轴（0-3s/3-8s…）
│   ├── voiceover.txt        VO/台词逐句（驱动配音）
│   ├── 时间轴.json          段落级时间分配
│   ├── storyboard.json      分镜（实测时长驱动）+ visual_contract 种子
│   ├── 镜头时长.json
│   ├── 字幕_zh.srt / 字幕_en.srt
│   └── 广告法机检报告.json   ad_law_check.py 产物（命中=block）
├── 设定库/                  global_style + 角色卡 + 场景卡 + 产品卡 + voicemap.json
├── 配音/                    line_NN.wav + vo.wav + 时长清单.json + voice_qc.json + _voicecache/
├── 出图/共享/ 出图/分镜/     prompt/ + 图片/（三层定妆库 + 逐镜首尾帧）
├── 出视频/分镜/             prompt/ + 视频/（每 Clip MP4 + video_model_routes.json + video_qc.json）
├── 合成/                    成片/cutdown/多比例 + delivery/color/rendered_text/asr/accessibility QC
├── 合规/                    locale_matrix + release_variant_manifest + provenance_qc + compliance + M0 + human_signoff
├── 投放反馈/                experiment_plan.json + experiment_plan_validation.json + raw/ + feedback_report.json
└── 成片_主片.mp4
```

## brief 必填分层（一句话入口的机器判据，`contract.brief_check()`）

| 层 | 字段 | 约定 |
|---|---|---|
| **必问最小集** `BRIEF_REQUIRED` | `brand` `product` `usp` `audience` `campaign_objective` | 缺任一 `ready=false`，先补齐再开工创意；广告目标决定创意/评分权重 |
| 推断 + 一次确认 | 调性/key_message/主片时长/平台/创意路线 | AI 给推断值打包让用户一次确认（与 `_设置.md` 选择点合并问），不算必填 |
| **花钱前闭合项** `BRIEF_DEFER_TO_GATE` | `claims` `rights` `mandatories.legal_lines` `measurement.primary_kpi` `measurement.conversion_event` | 可先做探索，但 `gate_ready=false` 时禁入 image/video/compose；claim 还须按 `evidence_type` 补来源、方法、条件、范围、有效期和批准人 |

发布前另须写 `brief.placements`，并把当前官方安全区/遮挡模板证据写进 `brief.platform_safe_zone_evidence.{平台:placement}`；未知版位在 `brief.placement_specs` 录入客户/官方确认规格。只有平台名、没有版位时可继续做母版，但 compliance manifest 不给 release-ready。

空串/空列表/「待补」/「TBD」都算缺。

`rights` 必须结构化：`status/territory/media_scope/approved_by`；实际使用项还要 `evidence_file/validity`，授权项另要 `valid_from/valid_until`。裸字符串“已授权/自有”只算迁移输入，不给付费 gate 或 release-ready。

## 阶段表

| key | 阶段 | owner | gate |
|---|---|---|---|
| `brief` | 客户需求立项 | `ad` | brief.json |
| `concept` | 创意策划 | `ad-concept` | concept.md + 创意脚本 |
| `script` | 广告脚本+VO+时间轴 | `ad-script` | 广告法机检 + voiceover.txt |
| `voice` | VO配音 | `ad-voice` | 时长清单.json |
| `storyboard` | 分镜（实测时长驱动） | `ad-script` | storyboard.json + 镜头时长 |
| `image` | 定妆库+出图 | `ad-image` | visual identity + 首尾帧 + product_qc（高风险闸门）|
| `video` | 图生视频 | `ad-video` | 契约继承 + clip videos + video_qc（高风险闸门）|
| `compose` | 剪辑包装+交付 | `ad-compose` | 成片 + cutdown + 技术/色彩/最终文字/ASR/无障碍 QC（高风险闸门）|
| `handoff` | AI披露/发布合规 | `ad-craft` | locale + 实际 provenance + release variant + compliance release-ready |
| `review` | 质检自审 | `ad-review` | 最终媒体 contact sheet + M0 + 具名逐项 SHA 绑定签收 + 上游依赖收据 current |
| `feedback` | 投放反馈（可选） | `ad-feedback` | 预注册单变量实验 + 原始数据绑定 + 有边界的统计读取 |

> **不拆集**：一条主片是整体；`_进度.md` 用「阶段进度表」而非逐集矩阵。
> **音频先行**：VO 实测时长驱动镜头时长，`script` 跑两遍（脚本 pass → 配音后 `storyboard` pass）。广告常是「音乐床 + VO」混合驱动，音乐床作为节奏锚一并记录。

## 逐阶段验收（单一真值源）

`contract.STAGE_CRITERIA` 为每个阶段声明标准与证据性质，`stage_acceptance.py` 执行并写 `生产数据/stage_acceptance/<stage>.json`：

- `deterministic`：文件、哈希、时长、编解码、实测 QC 等机器事实。
- `official`：法律、监管或平台当前书面规格；产物必须保留来源和采集日期。
- `house`：内部生产母版/流程阈值，必须明确写作内部标准，不冒充平台统一要求。
- `human`：产品视觉真实性、人物/场景语义、字幕感知、钩子质量等机器不能可靠裁决的项目，由具名人员逐项签收。
- `heuristic`：创意/视觉启发式，只能给建议或 WARN，不能伪装效果保证。

```bash
python3 skills/ad/ad-craft/scripts/stage_acceptance.py "<作品根>" --stage voice
python3 skills/ad/ad-craft/scripts/stage_acceptance.py "<作品根>" --stage review
```

`progress_set.py set-stage ... --status ✅` 会先执行当前阶段验收，并写当前输入/输出 `dependency_receipts.json`；未通过不得手工制造完成状态。正式 image/video/compose runner 也会验上游。`--mode rough` 只允许明确的占位预览降级，正式完成仍用 `formal`。

旧作品先跑 `migrate_project.py`（默认 dry-run），确认后 `--write`。迁移会备份原件、升级 schema/locale/阶段表并生成依赖图；旧 ✅ 只有在当前 acceptance 与已有哈希收据同时成立时才保留，未知授权、法务和人工判断绝不自动补成 approved。

各阶段入场、通过线、依据和失败回退的完整人读表见 `production-standards.md`；字段仍以 `contract.STAGE_CRITERIA` 为机器真值。

## cutdown / 多版本轴（不拆集的并行轴）

一条主片派生多个**交付件 deliverable**，登记在 `_进度.md` 的「交付版本矩阵」：
- `kind`：`master`（主片）/ `cutdown`（多时长 30→15→6s）/ `reframe`（多比例 16:9/9:16/4:5/1:1）/ `ab_variant`（A/B）。
- 字段：`deliverable_id / label / duration / aspect / kind / spec / status / path`。
- `ad-compose` 据此重剪 cutdown、reframe 比例、按 `交付规格` 归一响度（LUFS）和安全框。
- `交付规格=自定义` 时必须在 `brief.delivery_profiles.自定义` 留 `loudness_lufs/true_peak_db/source/checked_at/approved_by`；不得把内部 -16 LUFS 悄悄当客户自定义值。

## 关键选择点（详见 `skills/ad/ad-craft/references/选择点与偏好.md` 拍广告节）

`广告类型` `广告目标` `漏斗阶段` `创意路线` `基础视觉风格` `主片时长` `交付比例` `cutdown版本` `生图模型` `生图渠道` `一致性增强` `生视频模型` `生视频渠道` `视频模型路由` `出视频规格` `视频分辨率` `配音后端` `音乐来源` `品牌包装模板` `字幕语言` `AI视觉使用披露` `广告法地区` `交付规格` `生成粒度` `目标平台` `发行地区`。

合规/不可逆/花钱多的点（`广告法地区`、`音乐来源`）即便记录过每次仍确认。

> 产线不替发布者点击平台声明，也不对所有地区硬烙同一种水印；但发布声明证据、显式标识责任和元数据状态必须进入 compliance manifest，最终 review 消费它。

## 核心资产深层身份 (Hero Asset Deep Identity)

Hero Product (`PROD_xx`) 需在 `asset_registry.json` 中额外锁定以下字段：
- **资产 ID 强绑定**：产品/App/UI/片尾 end card 这类语义产品镜头，分镜或 prompt 必须显式引用 `PROD_*`；品牌/logo/CTA 镜头必须显式引用 `BRAND_*`。
- **Logo 保护区 (Logo Mask)**：定义 Logo 的精确 HEX 色值、最小留白比例及在包装上的网格坐标。
- **品牌色色度锁 (Hex-Lock)**：不仅文字描述，Prompt 中需显式包含品牌色 HEX 代码。
- **状态追踪 (Interaction States)**：记录产品的物理状态（满瓶/倾倒/冷凝水/爆裂）。
- **App/UI 状态锁**：App 广告需记录屏幕状态、关键 UI 文案、按钮/CTA 文案和不可漂移区域；图生视频 prompt 继承同一 `PROD_*`。

## 制片前控包 (Producer Pack)

进入付费出图前跑：

```bash
python3 skills/ad/ad-craft/scripts/producer_pack.py "<拍广告作品根>"
```

`producer_pack` 是传统广告 PPM/producer packet 的机器版，输出 `生产数据/producer_pack.json/md`。它把 brief、concept、storyboard 和 `_设置.md` 合并成一份制片对账表：

- shot list：每镜时长、画面、VO、产品/品牌资产 ID、交付比例和安全区。
- rights/claims/legal：授权与 claim 分型依据；检测/统计/文献/比较/代言按类型要求来源、资质、方法、条件、样本、范围、有效期和公开披露。
- asset gaps：缺 `PROD_*` 是 block；缺 `BRAND_*` 是 warn。
- approval checklist：付费生成前必须审批的产品、logo、包装、UI、CTA、法律声明和交付规格。

有 `approval_blocks>0` 时不得进入 image/video 花钱 gate。

## 平台交付包 (Platform Pack)

进入出视频/合成前跑：

```bash
python3 skills/ad/ad-craft/scripts/platform_pack.py "<拍广告作品根>"
```

`platform_pack` 把 brief 里的 `platforms`、`placements`、`deliverables` 和 `_设置.md` 里的目标平台/交付比例合并成 `生产数据/platform_pack.json`：

- placement_specs：TikTok feed/Out of Phone、YouTube Shorts/Demand Gen/in-stream、Meta Reels 的当前官方来源、采集日期、比例/时长/声音策略与安全区；抖音/小红书没有可公开稳定复用的当前模板时明确标为内部快照，必须由发布方绑定当前广告后台 placement 模板。
- deliverables：主片 + cutdown（如 30s/15s/6s）的机器行，供 `_进度.md` 和合成交付矩阵对齐。
- findings：只有平台名而无 placement 记 warn，并在 release 阶段升级为 block；未知版位或无出处的自定义规格直接 block；自定义规格至少填 `aspect|allowed_aspects/safe_area/source/checked_at`。安全区证据必须 placement-specific。
- deliverable mapping：多版位项目用 `brief.deliverable_placements.{deliverable_id}` 显式映射；每件只验自己的 placement，缺映射或版位无交付件直接 block。

## locale、发布变体与内容哈希

`locale_matrix.json` 逐 locale 统一翻译、币种、单位、CTA、法律声明、VO、字幕和文字布局，并把每个 deliverable 显式映射到 locale。`release_variant_manifest.json` 再把每个实际文件串成：`deliverable → SHA → placement → locale → jurisdiction → claims/disclosures → rights → AI label receipt`。

`compliance_manifest.py` 不再把「海外」当法律配置。中国大陆读取当前广告法报告；非大陆逐个 `release_regions` 消费 `brief.legal_reviews[]`，集合地区还须列 `jurisdictions`。每条复核必须由具名批准人绑定当前脚本、storyboard、主片和 delivery plan 的 `release_content_sha256`；创意或成片变化后旧法务意见自动失效。

## 最终媒体、文字、音频、无障碍与 provenance

- `compose_preflight.py --color-report` 在合成前识别 HDR/BT.2020/混合色彩源；无显式转换计划时 block，不能只改标签。
- `delivery_qc.py` 对最终文件核验 BT.709 primaries/transfer/matrix、tv range 和 progressive。
- `rendered_text_qc.py` 在最终编码文件上抽帧检查字幕/CTA/价格/claim/法律声明；OCR/对比度只定位，逐条具名确认文字、停留、遮挡并留证。
- `asr_consistency.py` 对批准 VO、实际 VO、字幕、最终音轨四路对账，关键数字/价格/CTA/claim/法律声明精确匹配。
- `accessibility_qc.py` 验字幕时间码、逐个非语言音频事件和项目要求的音频描述/媒体替代；阅读速度/闪烁/自动对比度明确为快筛。
- `provenance_qc.py` 实际探测最终文件 C2PA/隐式标识；只写 `metadata_status=preserve` 无效，外部回执必须绑定当前文件 SHA。
- `final_media_consistency.py` 从最终 clip 与最终编码交付件逐镜抽首/中/尾帧，按 product/character/scene/prop 生成 contact sheet；人工证据和 sheet hash 由 `human_signoff.py` 绑定。

## 跨比例构图启发式（不能替代平台安全区）

为了适配多比例（16:9/9:16/4:5/1:1）重分镜，可用 **8x8 网格**作前期构图启发式：
- **核心重心 (Visual Focus)**：核心卖点（USP）和产品 Logo 必须落在中心 **4x4 网格**内。
- **边缘容差**：画面外缘 2 格网格为“可裁切区”，禁止在此放置法律声明、CTA 或关键 USP。
- **边界**：中心网格不是“万能安全区”，也不能证明任何具体版位通过；发布前必须用实际平台、比例、caption、anchor/add-on 对应的官方模板或客户书面模板复核并留证。
