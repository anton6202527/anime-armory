# ad 生产阶段标准（2026-08-20）

机器真值是 `scripts/contract.py:STAGE_CRITERIA`，执行器是 `scripts/stage_acceptance.py`。本文件说明每一阶段为什么这样验、证据是什么、失败回哪里；不得只凭“看起来完成”手填 `_进度.md`。

## 判定语言

- `block`：确定性缺口、适用法律/平台书面要求未闭合、付费或发布所需证据缺失。不得进入下游正式阶段。
- `warn`：启发式、内部快筛、平台建议或机器不能可靠裁决的风险。必须处理或在具名人审中签收，但不能伪装成法律硬门槛。
- `official`：法律、监管或平台当前书面来源；必须带 URL/文件、`checked_at` 和适用范围。
- `house`：本项目内部生产标准；可被客户/媒体书面规格覆盖，但覆盖必须留证。
- `human`：机器不能判断的语义、真实性、感知与最终版位项目；签收人、证据和媒体 SHA 必须当前有效。

## 11 阶段验收表

| 阶段 | 入场条件 | 完成标准 | 证据/通过线 | 失败回退 |
|---|---|---|---|---|
| `brief` | 客户目标可访谈 | 品牌、产品、USP、受众、广告目标齐；花钱前 KPI/转化事件齐 | `brief_check.missing_required=0`；测量字段非占位 | `ad-concept` 补访谈 |
| `concept` | brief 最小集齐 | `concept.json` 的 Big Idea、key message、目标、创意假设、强制项结构完整且 formal 目标与 brief 一致 | JSON 缺失/空/畸形/结构错误 block；Markdown 仅人读视图 | `ad-concept` 补写/重做机器合同 |
| `script` | concept 当前有效 | 脚本、VO、时间轴可解析；广告法报告当前且 0 block | 三文件非空；`广告法机检报告.summary.block=0` | `ad-script` 删改/补法务依据 |
| `voice` | voiceover 锁定 | 每句真实音频、voice key、实测秒数和整轨一致 | formal 无占位；`voice_qc` full precision、0 block | `ad-voice` 重录/重导 |
| `storyboard` | 真 VO 时长可用 | 唯一镜号、正时长、总时长、VO、强制项、接缝和 claim 披露通过 | `镜头时长.json` 0 block；claim_id 与披露呈现合同闭合 | `ad-script` 重排分镜/披露 |
| `image` | storyboard 已验；exact 阶段预算包有效 | 逐 job 串行完成 preflight→真实提交/收集→full product QC→绑定当前输出 SHA 的六项具名人审；包内不重复付费确认 | 每个非取消 job `image_job_receipt.status=accepted`；下一 job 不得越过未签收前序（B14） | `ad-image` 补参考/QC/人审或重出当前图 |
| `video` | image 已验；exact 阶段预算包有效 | prompt、输入帧、模型路由与实际请求绑定当前 render profile；回收媒体实测；clip 技术/接缝通过；未知保守成本上界不提交 | job/profile SHA 当前；requested 与 ffprobe `observed_output` 均符合 `source_generation`；`contract_inheritance`、`video_qc` full、0 block | `ad-video` 修规格、clip/接缝 |
| `compose` | video 已验 | adaptation approved 且 actual execution receipt 当前；每件符合 `master_render` 并通过技术、色彩、最终像素文字、ASR、无障碍和 provenance | adaptation plan/item + actual mode + 输入/输出/profile SHA 对账；delivery QC 绑定当前 plan/media/profile/adaptation；容器放大只能写 `container_upscale_only`，原生要求不足则 block | 原生重剪/重做、获准机械裁切或对应版本重导 |
| `handoff` | 全部交付件已定 | locale 与逐变体链闭合；AI 标识/商业披露双收据和 formal campaign readiness 均当前 | locale/provenance/release variant/readiness 0 block；`compliance_manifest.release_ready=true` 且全部证据 SHA 当前 | 发布方/法务/本地化/measurement 负责人补证 |
| `review` | handoff 已验 | M0 当前；最终 clip/交付件逐镜首中尾帧 contact sheet 与机器不可判项由具名人员逐项签收 | M0 0 block；全部媒体、逐资产 contact sheet、人工证据 SHA 当前；上游依赖收据 current | 只回 stale 节点或补审片 |
| `feedback` | 当前 formal campaign readiness + 投放前 canonical 计划存在 | 同版位/受众/预算、单变量、KPI、baseline/MDE/alpha/power、固定停止规则和多重比较预注册；validation 从计划重算；报告绑定当前 brief/readiness/素材/平台配置与结果回执/证据/canonical raw | 只有 `analysis_status=complete` 可验收；平台原生正式结果优先；本地二项分析只有功效样本与停止条件完成、比较校正通过才可 qualified，否则 directional/interim | 延长实验、补平台回执或重做设计 |

## claim 引证依据合同

`brief.claims[]` 每条必须有稳定 `id` 和 `evidence_type`。通用必填：

`claim / evidence_type / evidence / evidence_file / method / evidence_date / territory / approved_by`

条件字段：

- `test_measurement`：`issuer / issuer_qualification / method_standard / test_conditions / sample`。
- `statistics_survey`：`statistical_method / sample_size / sample_definition / representativeness / survey_period / bias_limitations`。
- `scientific_literature`：`publication / publication_locator / applicability_basis`。
- `comparison`：`comparison_target / comparison_basis / same_conditions`。
- `testimonial`：`endorser_authorization / typicality_basis / material_connection_disclosure`。
- 使用引证内容时另填 `source_name / source_locator / applicable_scope / validity / display_disclosure`。

依据是市场监管总局 2026 年《广告引证内容执法指南》对真实性、来源可查询、检测/统计方法、实验条件、样本局限、适用范围和有效期的要求。`producer_pack` 验证依据，`finalize_storyboard` 验证呈现，`cutdown` 用 `claim_id` 防止短版只保留宣称却砍掉披露。

## 披露呈现合同

承载宣称的镜头写 `claim_ids`；对应 `disclosures[]` 至少写：

```json
{
  "claim_id": "claim_01",
  "text": "适用条件/样本局限/免责声明",
  "source_text": "来源：某机构 2026Q2 报告",
  "duration_sec": 4,
  "font_height_ratio": 0.04,
  "contrast_review": "pass",
  "safe_zone_review": "pass",
  "relationship": "same_screen",
  "relative_prominence": "sufficient"
}
```

结构缺失或关系不成立是 block。内部 `12 字符/秒`、字高占画面 `3%` 只作 WARN 快筛，不是法定数值；最终以实际像素、真实版位和具名审片为准。

## 授权合同

`brief.rights.talent/music/fonts/assets` 不接受“已授权/自有素材”裸字符串。每项使用：

`status / territory / media_scope / approved_by`，其中 `status` 为 `not_used / owned / licensed / public_domain / client_supplied`。

- 非 `not_used` 另填 `evidence_file + validity`。
- `licensed` 另填 `valid_from + valid_until`；未生效、已到期或日期错误为 block。
- release manifest 将授权 `territory` 与每个发行地区对账；`全球/worldwide` 可覆盖全部，其他值须显式包含目标地区。
- 有多首音乐、多位艺人或多套资产时用数组逐项登记，不能用一个模糊状态覆盖整包。

## 平台与版位

`platforms` 只说明平台，`placements` 才决定安全区、比例、时长和声音策略。示例：

```json
{
  "platforms": ["TikTok", "YouTube"],
  "placements": ["TikTok:auction_in_feed", "YouTube:demand_gen"],
  "platform_safe_zone_evidence": {
    "TikTok:auction_in_feed": "合规/tiktok-feed-current.png",
    "YouTube:demand_gen": "合规/demand-gen-current.png"
  }
}
```

未知版位写 `placement_specs.<平台:版位>`，至少有 `aspect|allowed_aspects / safe_area / source / checked_at`。平台级模板不能自动证明每个 placement；release 阶段要求 placement-specific 证据。

多版位项目还必须写 `deliverable_placements`，例如 `master → YouTube:in_stream`、`reframe_9x16 → TikTok:auction_in_feed`。每个交付件只消费自己的版位约束；缺映射、未知版位或有版位无交付件均 block。`reframe_9x16` 只是历史交付件 ID，不等于批准机械裁切；执行模式只认 `placement_adaptation.json`。

### 统一 render profile 与 placement adaptation

`render_profile.json` 把 `source_generation` 与 `master_render` 分开：route/job/runner 绑定源请求，compose/delivery 绑定母版。720p 源装入 1080p/4K 容器只能标 `container_upscale_only`；客户/版位要求原生细节而源不足时 fail-closed。

跨比例交付逐件选择 `native_master/native_recrop/native_reedit/native_variant/mechanical_reframe`。原生 reedit/variant 的 shot plan 须逐镜绑定 `source_path(s)` 与当前 SHA，execution receipt 必须实际消费这些源素材；recrop/mechanical 使用 focus plan。机械路径必须有具名批准、当前 placement 安全区证据、逐镜 focus plan，存在结构风险时另有 risk acceptance。中心网格与能跑通的 ffmpeg 命令都不是发布证据。

手工 NLE 原生重剪的 execution receipt 是具名执行人的可审计签收，不是从最终像素反推出编辑时间线的密码学证明；需要对抗恶意伪报时，应把 NLE timeline/OTIO/受控导出 runner 纳入项目证据。当前自动化只声称能阻断缺源素材、错模式、错计划或 SHA 漂移，不声称能识别刻意伪造的人工签收。

### 竖版信息流安全区快照（2026-08-20 核验·会过期，release 仍以当期版位证据为准）

设计首帧/字幕/CTA 可用中心网格做草图，但不保存易漂移的“万能像素边距”。当前一手口径是：

- TikTok In-Feed 的 safe zone 会随横竖比例、caption 长度及 anchor/add-on 改变；必须下载与本交付件相符的模板并在预览工具复核。
- Meta Reels 优先 9:16、有音频且关键信息位于 safe zone；使用 Meta 当前 safe-zone checker，而不是项目内固定百分比。
- YouTube Shorts 优先 9:16；横版/方版是否支持与具体 campaign/format 有关，须用 Google Ads 当前预览和规格页核验。
- TikTok Out of Phone 属于 sound-off 环境，应独立做字幕/画面可懂版本；billboard 指引为约 10–15 秒，仍以实际媒体 owner 模板为准。
- 烧录字幕须与平台 caption/CTA/互动覆盖层错开；`rendered_text_qc` 管最终像素可读性，`platform_safe_zone_evidence` 证明实际版位遮挡。

## 发行辖区

中国大陆由当前广告法机检和 claim 依据共同闭合。非大陆发行在 `legal_reviews[]` 为每个 `release_regions` 写：

`region / jurisdictions / status=approved / authority / source / checked_at / approved_by / evidence_file / content_sha256`

`content_sha256` 由 `compliance_manifest.release_content_sha256()` 对当前脚本、storyboard、主片和 delivery plan 合成。泛称“海外”“全球”不构成逐辖区复核；北美、东南亚、港澳台、全球等集合必须列 `jurisdictions`。

## locale 与逐交付发布变体

`合规/locale_matrix.json` 逐语言登记 `language / jurisdictions / currency / unit_system / cta / legal_lines / voiceover_path / subtitle_path / translation_review / typography_review`，并用 `deliverable_locales` 把每个未取消交付件映射到 locale。源语言可标 `source_language`，翻译与最终排版必须有具名、可查询证据；不能用“一份英文字幕”推定所有地区已本地化。

`release_variant_manifest.json` 是发布单一真值：每件记录最终文件 SHA、placement、locale、具体 jurisdiction、保留的 claim+disclosure、授权 media scope、法律复核，以及逐 placement 独立的 AI label receipt 与 commercial/paid-partnership disclosure receipt。二者不可互代；媒体或证据哈希改变后回执自动失效。

`campaign_readiness.json` 是投放单一真值：formal 须核落地页最终 URL/跳转、offer/claim/CTA/价格、行业×平台×辖区准入、conversion event 与 tag/pixel/SDK/CAPI diagnostics、归因/UTM/deep-link、consent/privacy，且只接受项目内证据。sample 可以保留 WARN 做样片，但永远不能 release-ready。

## 最终文字、ASR、无障碍与 provenance

- 内部 SDR 母版：H.264/yuv420p、BT.709 primaries/transfer/matrix、limited (`tv`) range、progressive、AAC 48 kHz。客户/HDR 规格可覆盖，但必须写显式转换方案和证据；不得把 HDR 直接改标签冒充 BT.709。
- `rendered_text_qc` 从每个最终编码文件抽取字幕、CTA、价格、claim、法律声明所在帧；OCR、像素对比度、停留时间和 bbox 用于定位，最终精确文字/对比度/时长/遮挡由具名人员逐项确认并绑定证据。
- `asr_consistency` 比较批准 `voiceover.txt`、实际 VO transcript、字幕和最终母版 transcript；普通全文相似度只 WARN，数字/价格/CTA/spoken claim/法律声明缺失或变化为 block。每份 transcript 另以 `asr_receipts.json` 绑定当前媒体 SHA、文本 SHA、引擎/模型和时间。
- 预录音频默认需要同步字幕；逐个有意义的音乐、音效和说话人事件必须在相同时间覆盖。按项目 WCAG 2.2 目标提供音频描述或媒体替代；阅读速度、自动对比度和低分辨率闪烁只作快筛。
- `provenance_qc` 直接对最终文件运行 c2patool/ffprobe。容器不承载或本地缺工具时，只接受写明工具/时间/批准人/可查询输出且绑定当前媒体 SHA 的外部探测回执；`metadata_status=preserve` 不是证据。

## 逐资产依赖哈希与旧项目迁移

`artifact_dependency_graph.json` 对阶段、逐镜 image/video、逐交付 compose 记录输入/输出 SHA；`dependency_receipts.json` 只在阶段真实验收时写入。brief、产品包装、claim、字幕或 clip 变化后，`stale_input/output_changed` 精确指出要返工的镜头/交付件；输入变了但输出完全没重做时拒绝重新验收。旧项目用 `migrate_project.py` dry-run→`--write`，原文件先备份，旧 ✅ 不继承，未知权利/法务/人工判断保持 pending。

**新鲜度分层（设计说明）**：产线故意用两种新鲜度证据，强度不同、职责不同——① **SHA 收据（强）**：依赖图/发布变体链/人审签收全部内容寻址，`touch`、时钟回拨、mtime 不前进都骗不过它，是"能不能发布"的唯一强证据；② **mtime 序（弱）**：`stage_acceptance.stale()`/gate 报告新鲜度/QC 报告晚于产物这类检查用文件时间序，只回答"要不要重跑一次"，成本低、无需读全量内容。弱层可被伪造，但伪造 mtime 混过验收后仍会在 review 阶段被 SHA 层拦下（依赖收据 current + 签收哈希绑定当前媒体）。因此：给弱层加检查项是廉价预警，把弱层"升级"成 SHA 不是免费午餐（每次验收都要重算全量哈希），除非某文件已进依赖图，否则维持 mtime 口径是刻意取舍，不是疏漏。

## 例外与覆盖

例外必须同时满足：具体范围、理由、批准人、日期、证据文件/记录、所绑定的当前产物哈希。任何“先放行后补”“手填 ✅”“通用海外”“平台默认应该可以”都不是有效例外。

## 当前一手来源

- 市场监管总局《广告引证内容执法指南》：<https://policy.mofcom.gov.cn/claw/clawContent.shtml?id=106104>
- TikTok Auction In-Feed specs：<https://ads.tiktok.com/resources/help/article/tiktok-auction-in-feed-ads?lang=en>
- TikTok Out of Phone：<https://ads.tiktok.com/resources/help/article/creative-guidelines-for-tiktok-out-of-phone?lang=en>
- TikTok landing-page review：<https://ads.tiktok.com/help/article/ad-review-checklist-landing-page?lang=en>
- TikTok commercial content disclosure：<https://ads.tiktok.com/resources/help/article/about-the-commercial-content-disclosure-setting-for-advertisers?lang=en>
- Google video ad specs：<https://support.google.com/google-ads/answer/17091270?hl=en-GB>
- Google Demand Gen specs：<https://support.google.com/google-ads/answer/17091672?hl=en>
- Google destination requirements：<https://support.google.com/adspolicy/answer/6368661?hl=en-GB>
- Google enhanced-conversion diagnostics：<https://support.google.com/google-ads/answer/13258081?hl=en>
- Meta Reels ads：<https://www.facebook.com/business/ads/facebook-instagram-reels-ads>
- W3C WCAG captions：<https://www.w3.org/WAI/WCAG22/Understanding/captions-prerecorded>
- W3C WCAG flashes：<https://www.w3.org/WAI/WCAG22/Understanding/three-flashes-or-below-threshold>
- W3C WCAG 2.2：<https://www.w3.org/TR/WCAG22/>
- 中国《人工智能生成合成内容标识办法》：<https://www.cac.gov.cn/2025-03/14/c_1743654684782215.htm>
- C2PA Technical Specification 2.3：<https://spec.c2pa.org/specifications/specifications/2.3/specs/_attachments/C2PA_Specification.pdf>
- Google Ads AI content labels：<https://support.google.com/google-ads/editor/answer/17231795?hl=en>
