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
2. **卖点-免责联动 (USP-Disclaimer Linkage)**：脚本里做了**受规管的功效/收益宣称**，就必须配对应免责声明，否则违规。脚本阶段写文案时按此映射主动补 `legal_lines`，分镜定稿由 `finalize_storyboard.py` 的 `usp_disclaimer_check` **机检兜底**（扫 `广告脚本.md`+`voiceover.txt`+分镜命中宣称 → 分镜 `legal_lines`/字幕里必须有对应免责之一）：金融理财（年化/理财/收益率）→「投资有风险，入市需谨慎」、加盟招商→「加盟有风险，投资需谨慎」、保健食品→「本品不能代替药物」**=法定强制·缺则 block**；化妆品功效（美白/抗皱）、减肥、教育效果→「效果因人而异」**=平台强烈要求·缺则 warn**（表述多变交人判）。每条命中带 `suggestion`（该补哪句免责）。与广告法机检互补：一个拦「不能说的词」，一个拦「说了就得配免责」。
3. 按 `主片时长` 写 `广告脚本.md`：逐段**秒级时间轴**。
4. **版位安全区布局**：消费 `platform_pack` 的 placement/overlay-aware 约束；未知平台或没有当前遮挡模板时 block 补规格，不用固定中心网格冒充平台适配。
5. **CTA 与转化事件同构**：CTA 必须指向 brief 的 conversion_event/landing page，平台具体交互文案以当前官方版位能力为准，不凭记忆硬编码“左滑/扫码”。
3. 抽 VO/台词逐句写 `voiceover.txt`（驱动配音）；段落时间分配写 `时间轴.json`。
4. **跑广告法机检（硬闸门）**：
   ```bash
   python3 skills/ad-script/ad_law_check.py "<作品根>" --region 中国大陆 --json "<作品根>/脚本/广告法机检报告.json"
   ```
   🔴 block（国家级/遥遥领先/治愈/100%有效/祛斑生发/保收益/全网最低价/**升值空间·投资回报**/**医疗级**/**驰名商标·国家免检**/**升学率·提分保证**…）必须改；🟡 warn（裸"最"/海外绝对化与房地产降级/**数据引证待证：据调查·好评率无来源**/**时限诱导待证：今天最后·涨价在即**）结合资质与依据人判。每条命中带 **`suggestion` 改法**（如「升值/投资回报承诺→删除」「好评率→补来源样本」），照着改即可。改完复跑到 0 block。机检前先把文案**归一化**（NFKC+去零宽+去插空格+常见繁体→简体），`最 佳`/`１００％`/`療效`/`醫療級` 等绕过手法照样命中。报告写 `脚本/广告法机检报告.json`（含 `region`/`disabled`/`summary`/`findings[].suggestion`，`--region 关闭` 也照写 `disabled:true`）。也扫 `storyboard.json`（递归 frame/legal_lines/字幕）与 `字幕_英文.srt`。
5. 回写 `_进度.md` 脚本 ✅，提示下一步 `ad-voice`。

### 分镜 pass（配音后回跑）
1. 读 `配音/时长清单.json`（实测 VO 时长）。
2. 按实测时长把脚本拆成镜头/Clip，写 `storyboard.json`（含 `visual_contract` 种子：品牌色/光位/构图、每接缝 `continuity.transition` + `need_end_frame`）+ `镜头时长.json` + `字幕_zh.srt`（按 `字幕语言` 决定是否出英）。
3. **跑分镜定稿闸门**：
   ```bash
   python3 skills/ad-script/finalize_storyboard.py "<作品根>" --master 30s --json "<作品根>/脚本/镜头时长.json"
   ```
   对账分镜总时长≈主片目标（超/欠都报，容差随主片长度缩放 `max(0.5, master*0.03)`；缺 `--master` 时退读 `_设置.md` 主片时长，仍缺则 warn 不静默放过）、整片 + **单镜** VO 不被截断、**强制项落镜**（brief mandatories logo/slogan/法律声明/CTA 缺一即 block）、**USP↔免责联动**（`usp_disclaimer_check`：做了金融/加盟/保健等受规管宣称却缺对应免责=block，化妆品/减肥/教育功效缺免责=warn，见脚本 pass 第 2 条）、接缝有 transition。**占位 VO 默认硬拦**（看时长清单顶层 `has_placeholder`），rough preview 用 `--allow-placeholder` 或 `FINALIZE_ALLOW_PLACEHOLDER=1` 放行。block 经 `脚本/镜头时长.json` 流进 ad-craft 花钱 gate。
4. 0 block 后回写 `_进度.md` 分镜(实测时长驱动) ✅，提示下一步 `ad-image`（⚠️ 花钱 gate：先确认 `生图AI`/`一致性增强`，并补齐 brief 可延后合规项——`ad-craft/scripts/progress.py` 会列缺项）。

## 广告专有强化

- **《广告法》违禁词硬闸门**（差异化核心）：`ad_law_check.py` 内置绝对化用语（含第九条明禁的驰名商标/国家免检）/医疗保健极限词（含医疗级·医用级器械混淆）/化妆品禁用功效/金融教育不可证承诺（保证收益·刚兑·升学率·提分保证）/迷信/促销欺诈/**房地产违规（升值·投资回报承诺）**词库，再加两类 warn：**数据引证待证**（据调查/好评率/复购率无来源）与 **时限诱导待证**（今天最后/涨价在即）。含市场监管总局案例补充 + 归一化绕过防护 + 白名单降噪（最后/最初/第一时间…不误杀）+ **每条命中带 `suggestion` 改法**，带 pytest。命中 block 退出码非零。海外仅绝对化与房地产降 warn，促销欺诈（FTC/EU）仍硬 block。
- **总时长是硬约束**：广告 30s 就得 30s，`finalize_storyboard.py` 对账超/欠。
- **强制项落镜**：brief 的 logo/slogan/法律声明/CTA 必须在脚本里有对应镜头/字幕条（片尾包装由 `ad-compose` 做 end card）。
- **黄金 3 秒**：脚本第一段必须是钩子镜（信息流划走率最高的窗口）。

## 测试

```bash
cd skills/ad-script && python -m pytest test_ad_law_check.py test_finalize_storyboard.py
```

## 常见错误

| 错误 | 纠正 |
|---|---|
| 脚本写"最/第一/国家级/治愈/100%有效" | 广告法机检 block，改合规表述并留 claim 依据 |
| 配音前就锁死镜头时长 | 镜头时长由配音后实测 VO 驱动；脚本阶段只给段落秒级预算 |
| 分镜总时长不等于主片目标 | `finalize_storyboard.py` 会报；超了投不出去，欠了不饱满 |
| 漏了强制项 logo/slogan/法律声明 | brief 硬约束，脚本/片尾必须覆盖 |
| 关掉广告法机检图省事 | 仅非中国大陆投放且用户明确才 `--region 关闭`；默认从严 |
