---
name: ad-script
description: 拍广告 第2阶段·脚本 + 第4阶段·分镜（配音后回跑）+ 《广告法》违禁词机检。脚本 pass：把 创意/创意脚本.md 转成 广告脚本.md（画面+台词+VO旁白+秒级时间轴 0-3s/3-8s）+ voiceover.txt + 时间轴.json，并跑 ad_law_check.py 拦绝对化用语/医疗极限词。分镜 pass（配音后）：用 配音/时长清单.json 实测时长生成 storyboard.json + 镜头时长.json + 字幕，finalize_storyboard.py 对账总时长≈主片目标。ad-* 自包含。Use when writing 广告脚本/广告分镜, checking 广告法/违禁词/极限词, or finalizing storyboard timing. Triggers 广告脚本, 广告分镜, 脚本, 分镜, 时间轴, voiceover, 广告法, 违禁词, 极限词, 绝对化用语, storyboard, 镜头时长, ad-script.
---

# ad-script — 拍广告 · 脚本 + 分镜 + 广告法机检

两遍制：
- **脚本 pass**（配音前）：`创意/创意脚本.md` → `广告脚本.md`（画面+台词+VO+秒级时间轴）+ `voiceover.txt` + `时间轴.json`，并跑**《广告法》违禁词机检**。
- **分镜 pass**（配音后回跑）：用 `配音/时长清单.json` 的**实测 VO 时长**生成 `storyboard.json` + `镜头时长.json` + 字幕，`finalize_storyboard.py` 对账**总时长≈主片目标**（广告总时长是硬约束）。

**自包含**：只使用 ad-script 自己的脚本、references 和产物契约。

## 偏好（私有）

按 `../skills/ad-craft/references/选择点与偏好.md` 读 `<作品根>/_设置.md`。涉及：`主片时长`、`基础视觉风格`、`字幕语言`、`广告法地区`、`生成粒度`。`广告法地区`（合规点）每次确认；`关闭` 仅非中国大陆投放且用户明确时。

## 工作流

### 脚本 pass（配音前）
1. 读 `创意/concept.md` + `创意脚本.md` + `需求/brief.json`。
2. **claim 依据 + 呈现双合同**：先在 brief 为每条宣称设稳定 `id/evidence_type`，由 producer pack 按品牌事实/检测/统计/文献/比较/代言分别核验依据。受规管功效/收益仍跑 `usp_disclaimer_check`；金融/加盟/保健缺风险提示为 block，化妆品/减肥/教育等语境型项目为 WARN+人判。凡使用检测、统计、文献或比较引证，还必须准备来源、实验条件、样本局限、适用范围、有效期和 `display_disclosure`，不能先写大字数据再“后补证明”。
3. 按 `主片时长` 写 `广告脚本.md`：逐段**秒级时间轴**。
4. **版位安全区布局**：消费 `platform_pack.placement_specs`；只写平台名不足以确定安全区/时长/声音策略。未知 placement 或没有当前遮挡模板时先补规格，不用固定中心网格冒充平台适配。
5. **CTA 与转化事件同构**：CTA 必须指向 brief 的 conversion_event/landing page，平台具体交互文案以当前官方版位能力为准，不凭记忆硬编码“左滑/扫码”。
3. 抽 VO/台词逐句写 `voiceover.txt`（驱动配音）；段落时间分配写 `时间轴.json`。
4. **跑广告法机检（分层闸门）**：
   ```bash
   python3 skills/ad-script/ad_law_check.py "<作品根>" --region 中国大陆 --json "<作品根>/脚本/广告法机检报告.json"
   ```
   🔴 block（国家级/最高级/最佳、治愈/100%有效、祛斑生发、保收益、虚假最低价、**升值/投资回报**、**医疗级**、**驰名商标/国家免检**、**升学率/提分保证**…）必须改；🟡 warn（最新/领先/销量第一/唯一/100% 等上下文型比较、裸"最"、**数据引证待证**、**时限诱导待证**）必须补比较范围、时间、地区、样本、出处并由具名人员复核；不能完整举证或可能误导就删改。此分层依据市场监管总局《广告绝对化用语执法指南》，机器只做初筛，不自动宣判语境型表述违法。每条命中带 `suggestion` 与 `evidence_required`。改完复跑到 0 block；warn 在最终 `human_signoff` 中签收。归一化仍会识别 `最 佳`/`１００％`/`療效`/`醫療級` 等绕过写法。报告含权威来源与采集日期，也递归扫描 storyboard/字幕。
5. 回写 `_进度.md` 脚本 ✅，提示下一步 `ad-voice`。

### 分镜 pass（配音后回跑）
1. 读 `配音/时长清单.json`（实测 VO 时长）。
2. 按实测时长把脚本拆成镜头/Clip，写 `storyboard.json`（含视觉契约、接缝、承载宣称的 `claim_ids` 与对应 `disclosures[]`）+ `镜头时长.json` + 字幕。披露字段与示例见 `references/script_format.md`。
3. **跑分镜定稿闸门**：
   ```bash
   python3 skills/ad-script/finalize_storyboard.py "<作品根>" --master 30s --json "<作品根>/脚本/镜头时长.json"
   ```
   对账总时长/单镜 VO/强制项/接缝/占位 VO；另用 `claim_presentation_check` 验 claim→镜头→披露关系、来源文字、同屏/紧邻、计划字高/停留、对比与版位复核字段。结构缺失 block；内部 12 字符/秒与 3% 字高只发 WARN，不冒充法定数值。完整依据见 ad-craft `production-standards.md`。
4. 0 block 后回写 `_进度.md` 分镜 ✅，提示下一步 `ad-image`（⚠️ 花钱 gate：确认具体 `生图模型`+`生图渠道`/一致性增强，并补齐 brief 可延后合规项）。

## 编剧轴 advisory 机检（"审"不是"门"·全部只提示不阻断）

既有的两个闸门（`ad_law_check` = 纯词表零语义；`finalize_storyboard` = 时长算术 + 字段存在性）
**都不看内容说了什么**。下面三个补的是这块，与 `ad-score` 的钩子/露出/CTA prescore 正交：

```bash
python3 skills/ad-script/scripts/idea_payoff_ledger.py "<作品根>" --write   # 创意承诺→分镜兑现
python3 skills/ad-script/scripts/copy_quality_audit.py "<作品根>" --write   # VO 文案质量
python3 skills/ad-script/scripts/shot_variety_audit.py "<作品根>" --write   # 分镜视觉多样性（出图前）
```

- **`idea_payoff_ledger`（创意承诺兑现账本）**：`创意/concept.json` 的 big idea / key message /
  usps / KV / storyline 是**种下**，`storyboard.json` 的镜头是**兑现**。此前 `producer_pack` 只把
  Big Idea **抄进** pack，全线无人回头核对分镜是否真的兑现了它。账本落 `创意/idea_payoff_ledger.json`。
  抓 `key_message_unrealized`（主张无任何镜承载）、`usp_unrealized`、**`usp_offledger`**（分镜冒出
  concept 未登记的卖点＝创意漂移/临时加戏）、`kv_unrealized`。
  **纪律**：镜头有结构化 `usp_ids`/`claim_ids`/`section` 时才高置信对账；没有时退到弱匹配**只产
  candidate、不宣判**（文本匹配不可靠）；增量合并**绝不覆盖已填的 payoff_shots**。
- **`copy_quality_audit`（文案质量）**：`redundant_vo_pair`（同义反复）、`repeated_usp_mention`
  （同卖点反复＝30s 里白烧秒数）、`empty_adjective_stack`（套话堆砌）、`vo_density`（字/秒过密）。
  **两条广告专有的防误报设计**：① **品牌名/slogan/CTA/法律声明的重复是刻意手法**（重复曝光提升
  recall），冗余检测按 brief mandatories + registry 品牌资产**排除**它们，否则全线误报；
  ② 与 `ad_law_check` **去重**——已被广告法机检命中的片段不再重复报（套话表与绝对化用语表本就重叠）。
- **`shot_variety_audit`（分镜视觉多样性·出图前最省钱的点）**：ad 的一致性套件（product_qc /
  reference_planner / asset_drift_report）全在保**资产不漂**，没有东西查**镜头设计是否重复单调**。
  参照 n2d `audit_shot_variety`＋`redundancy_audit` 补这条视觉不重复轴：`duplicate_shot_composition`
  （同景别/场景/机位反复）、`duplicate_shot_description`（画面描述 char-2gram≥0.6 近重复·分镜没结构
  字段时也能抓）、`scene_monotony`/`framing_variety_low`（长片单场景/单景别，只 info）。
  **广告专有收敛**：① 产品 beauty/特写、片尾 endcard、logo/CTA/价格板等**有意重复镜豁免**；
  ② 广告很短，单场景/单景别本就常见合法，故场景/景别单调只 info、不 warn。落 `生产数据/ad_shot_variety_audit.json`。

> 这几个（含 `ad-concept` 的 `concept_pack.py`）都由 gate 以 **advisory** 并入：报告缺失只 info，
> 报告里的 block 降为 warn。规矩见 `gate.py` 的 `score_findings`——**创意启发式只提示复核，
> 只有广告法与确定性闸门能 BLOCK**。想要硬闸的团队自己用 `--strict` 退出码。

## 广告专有强化

- **《广告法》分层闸门**（差异化核心）：`ad_law_check.py` 把第九条明确列举/失效背书、医疗/化妆品越界、金融教育不可证承诺、迷信、促销欺诈、房地产收益承诺作为 block；把最新/领先/销量第一等绝对化语境候选及数据引证/时限真实性作为 warn+补证。含官方执法指南来源、归一化绕过防护、白名单降噪和逐条改法。命中 block 非零；warn 必须在发布前具名复核，不能因机器未 block 就视为合法意见。
- **总时长是硬约束**：广告 30s 就得 30s，`finalize_storyboard.py` 对账超/欠。
- **强制项落镜**：brief 的 logo/slogan/法律声明/CTA 必须在脚本里有对应镜头/字幕条（片尾包装由 `ad-compose` 做 end card）。
- **2026 引证内容闭环**：producer pack 验依据，分镜验呈现，cutdown 验不拆散；来源、条件、适用范围和有效期不能只存在项目后台而不进入需要呈现的成片。
- **黄金 3 秒**：脚本第一段必须是钩子镜（信息流划走率最高的窗口）。

## 测试

```bash
cd skills/ad-script && python -m pytest test_ad_law_check.py test_finalize_storyboard.py
```

## 常见错误

| 错误 | 纠正 |
|---|---|
| 看到“最新/领先/第一”就机器定罪 | 明确法定项 block；语境型比较 warn+补时空范围/样本/出处+具名复核 |
| 配音前就锁死镜头时长 | 镜头时长由配音后实测 VO 驱动；脚本阶段只给段落秒级预算 |
| 分镜总时长不等于主片目标 | `finalize_storyboard.py` 会报；超了投不出去，欠了不饱满 |
| 漏了强制项 logo/slogan/法律声明 | brief 硬约束，脚本/片尾必须覆盖 |
| 数据宣称有报告，但分镜只放大字结果 | 用 `claim_ids` + `disclosures` 绑定来源/条件/范围/有效期；普通 legal_lines 不够 |
| 关掉广告法机检图省事 | 仅非中国大陆投放且用户明确才 `--region 关闭`；默认从严 |
