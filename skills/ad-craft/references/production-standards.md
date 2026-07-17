# ad 生产阶段标准（2026-07-11）

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
| `concept` | brief 最小集齐 | Big Idea、key message、目标、创意假设、强制项落档 | 五组结构字段存在；ABCD/平台创意建议只作 WARN | `ad-concept` 重做策略 |
| `script` | concept 当前有效 | 脚本、VO、时间轴可解析；广告法报告当前且 0 block | 三文件非空；`广告法机检报告.summary.block=0` | `ad-script` 删改/补法务依据 |
| `voice` | voiceover 锁定 | 每句真实音频、voice key、实测秒数和整轨一致 | formal 无占位；`voice_qc` full precision、0 block | `ad-voice` 重录/重导 |
| `storyboard` | 真 VO 时长可用 | 唯一镜号、正时长、总时长、VO、强制项、接缝和 claim 披露通过 | `镜头时长.json` 0 block；claim_id 与披露呈现合同闭合 | `ad-script` 重排分镜/披露 |
| `image` | storyboard 已验；付费确认 | 全部 job 完成，具体模型/渠道、真实参考输入与输出可追溯 | manifest 非取消 job 全 done；`product_qc` full、0 block | `ad-image` 补参考/重出 |
| `video` | image 已验；付费确认 | prompt 编译、输入帧、模型路由、输出可追溯，clip 技术/接缝通过 | `contract_inheritance`、`video_qc` full、0 block | `ad-video` 修 clip/接缝 |
| `compose` | video 已验 | 每个未取消交付件通过技术、色彩、最终像素文字、ASR 四路、无障碍和实际 provenance 检查 | `delivery/color/rendered_text/asr/accessibility/provenance` 均 0 block | `ad-compose` 对应版本重导或补具名证据 |
| `handoff` | 全部交付件已定 | locale 与逐变体链闭合：媒体 SHA→placement→locale→jurisdiction→claims/disclosures→rights→AI label receipt | locale/provenance/release variant 0 block；`compliance_manifest.release_ready=true` 且内部 SHA 当前 | 发布方/法务/本地化负责人补证 |
| `review` | handoff 已验 | M0 当前；最终 clip/交付件逐镜首中尾帧 contact sheet 与机器不可判项由具名人员逐项签收 | M0 0 block；全部媒体、逐资产 contact sheet、人工证据 SHA 当前；上游依赖收据 current | 只回 stale 节点或补审片 |
| `feedback` | 投放前计划存在 | 同版位/受众/预算、单变量、KPI/窗口/样本门槛预注册；报告绑定原始数据 | plan approved + SHA 当前；不可比/区间不足只能 `inconclusive` | 延长实验或重做设计 |

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

多版位项目还必须写 `deliverable_placements`，例如 `master → YouTube:in_stream`、`reframe_9x16 → TikTok:auction_in_feed`。每个交付件只消费自己的版位约束；缺映射、未知版位或有版位无交付件均 block。这样不会让横版主片被竖版规则误挡，也允许明确的 sound-off OOH 版本在字幕/视觉信息完整时无音轨交付。

### 竖版信息流安全区快照（2026-07 采集·会过期，release 证据仍以官方当期模板为准）

设计首帧/字幕/CTA 排版时的起点参考；数值随平台 UI 改版漂移（如 2026-01 TikTok 新增播放列表按钮使右侧死区扩 ~20px），**不得**代替 `platform_safe_zone_evidence` 的当期官方模板证据：

- 通用耐用规则（不易过期）：**80/60 规则**——关键文字/视觉放在画面中央 80% 宽 × 60% 高内；重要内容避开底部 25% 与右侧 15%。1080x1920 竖版的通用安全区约为居中 900x1400。
- TikTok（9:16）：避开顶部 ~130px、底部 ~484px、右侧 ~140px、左侧 ~44px；**买量广告**底部还要给 "Shop Now/Learn More" 按钮加 ~50px（合计 ~370px+ 底边距）。
- Instagram Reels：底部 ~25% 被 UI 遮挡（2025 末音频署名条又加高 ~50px）；Sponsored 标签 + Learn More 再吃 ~80px。
- YouTube Shorts：底部 ~30% 遮挡（订阅按钮 2025 末加大 30%，左下死区更大）；广告位底部有 Skip Ad / Visit Site。
- 三平台 2026 起默认开启 AI 自动字幕——成片若烧录字幕，位置要与平台自动字幕区错开，避免双字幕叠印（`rendered_text_qc` 管烧录字幕可读性，版位遮挡靠本快照 + 证据模板）。

## 发行辖区

中国大陆由当前广告法机检和 claim 依据共同闭合。非大陆发行在 `legal_reviews[]` 为每个 `release_regions` 写：

`region / jurisdictions / status=approved / authority / source / checked_at / approved_by / evidence_file / content_sha256`

`content_sha256` 由 `compliance_manifest.release_content_sha256()` 对当前脚本、storyboard、主片和 delivery plan 合成。泛称“海外”“全球”不构成逐辖区复核；北美、东南亚、港澳台、全球等集合必须列 `jurisdictions`。

## locale 与逐交付发布变体

`合规/locale_matrix.json` 逐语言登记 `language / jurisdictions / currency / unit_system / cta / legal_lines / voiceover_path / subtitle_path / translation_review / typography_review`，并用 `deliverable_locales` 把每个未取消交付件映射到 locale。源语言可标 `source_language`，翻译与最终排版必须有具名、可查询证据；不能用“一份英文字幕”推定所有地区已本地化。

`release_variant_manifest.json` 是发布单一真值：每件记录最终文件 SHA、placement、locale、具体 jurisdiction、保留的 claim+disclosure、授权 media scope、法律复核与逐素材 AI label receipt。重新编码后 SHA 改变，平台/AI label/法务回执自动失效。

## 最终文字、ASR、无障碍与 provenance

- 内部 SDR 母版：H.264/yuv420p、BT.709 primaries/transfer/matrix、limited (`tv`) range、progressive、AAC 48 kHz。客户/HDR 规格可覆盖，但必须写显式转换方案和证据；不得把 HDR 直接改标签冒充 BT.709。
- `rendered_text_qc` 从每个最终编码文件抽取字幕、CTA、价格、claim、法律声明所在帧；OCR、像素对比度、停留时间和 bbox 用于定位，最终精确文字/对比度/时长/遮挡由具名人员逐项确认并绑定证据。
- `asr_consistency` 比较批准 `voiceover.txt`、实际 VO transcript、字幕和最终母版 transcript；普通全文相似度只 WARN，数字/价格/CTA/spoken claim/法律声明缺失或变化为 block。每份 transcript 另以 `asr_receipts.json` 绑定当前媒体 SHA、文本 SHA、引擎/模型和时间。
- 预录音频默认需要同步字幕；逐个有意义的音乐、音效和说话人事件必须在相同时间覆盖。按项目 WCAG 2.2 目标提供音频描述或媒体替代；阅读速度、自动对比度和低分辨率闪烁只作快筛。
- `provenance_qc` 直接对最终文件运行 c2patool/ffprobe。容器不承载或本地缺工具时，只接受写明工具/时间/批准人/可查询输出且绑定当前媒体 SHA 的外部探测回执；`metadata_status=preserve` 不是证据。

## 逐资产依赖哈希与旧项目迁移

`artifact_dependency_graph.json` 对阶段、逐镜 image/video、逐交付 compose 记录输入/输出 SHA；`dependency_receipts.json` 只在阶段真实验收时写入。brief、产品包装、claim、字幕或 clip 变化后，`stale_input/output_changed` 精确指出要返工的镜头/交付件；输入变了但输出完全没重做时拒绝重新验收。旧项目用 `migrate_project.py` dry-run→`--write`，原文件先备份，旧 ✅ 不继承，未知权利/法务/人工判断保持 pending。

## 例外与覆盖

例外必须同时满足：具体范围、理由、批准人、日期、证据文件/记录、所绑定的当前产物哈希。任何“先放行后补”“手填 ✅”“通用海外”“平台默认应该可以”都不是有效例外。

## 当前一手来源

- 市场监管总局《广告引证内容执法指南》：<https://policy.mofcom.gov.cn/claw/clawContent.shtml?id=106104>
- TikTok Creative Best Practices：<https://ads.tiktok.com/help/article/creative-best-practices?lang=en>
- TikTok Out of Phone：<https://ads.tiktok.com/help/article/creative-guidelines-for-tiktok-out-of-phone>
- Google Demand Gen video specs：<https://support.google.com/google-ads/answer/17141078>
- Meta Reels ads：<https://www.facebook.com/business/ads/facebook-instagram-reels-ads>
- W3C WCAG captions：<https://www.w3.org/WAI/WCAG22/Understanding/captions-prerecorded>
- W3C WCAG flashes：<https://www.w3.org/WAI/WCAG22/Understanding/three-flashes-or-below-threshold>
- W3C WCAG 2.2：<https://www.w3.org/TR/WCAG22/>
- 中国《人工智能生成合成内容标识办法》：<https://www.cac.gov.cn/2025-03/14/c_1743654684782215.htm>
- C2PA Technical Specification 2.3：<https://spec.c2pa.org/specifications/specifications/2.3/specs/_attachments/C2PA_Specification.pdf>
- Google Ads AI content labels：<https://support.google.com/google-ads/editor/answer/17231795?hl=en>
