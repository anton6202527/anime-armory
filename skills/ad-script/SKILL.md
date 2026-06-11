---
name: ad-script
description: 拍广告 第2阶段·脚本 + 第4阶段·分镜（配音后回跑）+ 《广告法》违禁词机检。脚本 pass：把 创意/创意脚本.md 转成 广告脚本.md（画面+台词+VO旁白+秒级时间轴 0-3s/3-8s）+ voiceover.txt + 时间轴.json，并跑 ad_law_check.py 拦绝对化用语/医疗极限词。分镜 pass（配音后）：用 配音/时长清单.json 实测时长生成 storyboard.json + 镜头时长.json + 字幕，finalize_storyboard.py 对账总时长≈主片目标。ad-* 自包含，不复用 n2d-script。Use when writing 广告脚本/广告分镜, checking 广告法/违禁词/极限词, or finalizing storyboard timing. Triggers 广告脚本, 广告分镜, 脚本, 分镜, 时间轴, voiceover, 广告法, 违禁词, 极限词, 绝对化用语, storyboard, 镜头时长, ad-script.
---

# ad-script — 拍广告 · 脚本 + 分镜 + 广告法机检

两遍制（与 n2d 配音先行同构）：
- **脚本 pass**（配音前）：`创意/创意脚本.md` → `广告脚本.md`（画面+台词+VO+秒级时间轴）+ `voiceover.txt` + `时间轴.json`，并跑**《广告法》违禁词机检**。
- **分镜 pass**（配音后回跑）：用 `配音/时长清单.json` 的**实测 VO 时长**生成 `storyboard.json` + `镜头时长.json` + 字幕，`finalize_storyboard.py` 对账**总时长≈主片目标**（广告总时长是硬约束）。

**自包含**：不复用 `n2d-script`。可借鉴其分镜语法/接力链思路，落成 ad 自己的脚本与 references。

## 偏好（私有）

按 `../_偏好约定.md` 读 `<作品根>/_设置.md`。涉及：`主片时长`、`基础视觉风格`、`字幕语言`、`广告法地区`、`生成粒度`。`广告法地区`（合规点）每次确认；`关闭` 仅非中国大陆投放且用户明确时。

## 工作流

### 脚本 pass（配音前）
1. 读 `创意/concept.md` + `创意脚本.md` + `需求/brief.json`（强制项 logo/slogan/CTA/法律声明、claims、必避点）。
2. 按 `主片时长` 写 `广告脚本.md`：逐段**秒级时间轴**（`[0–3s] 钩子 / [3–8s] 痛点 / …`），每段写**画面 + 台词/VO + 音乐床/SFX 提示 + 镜头建议**。
3. 抽 VO/台词逐句写 `voiceover.txt`（驱动配音）；段落时间分配写 `时间轴.json`。
4. **跑广告法机检（硬闸门）**：
   ```bash
   python3 skills/ad-script/ad_law_check.py "<作品根>" --region 中国大陆 --json "<作品根>/脚本/广告法机检报告.json"
   ```
   🔴 block（国家级/最佳/治愈/100%有效…）必须改；🟡 warn（裸"最"/促销时限词）结合资质与依据人判。改完复跑到 0 block。
5. 回写 `_进度.md` 脚本 ✅，提示下一步 `ad-voice`。

### 分镜 pass（配音后回跑）
1. 读 `配音/时长清单.json`（实测 VO 时长）。
2. 按实测时长把脚本拆成镜头/Clip，写 `storyboard.json`（含 `visual_contract` 种子：品牌色/光位/构图、每接缝 `continuity.transition` + `need_end_frame`）+ `镜头时长.json` + `字幕_zh.srt`（按 `字幕语言` 决定是否出英）。
3. **跑分镜定稿闸门**：
   ```bash
   python3 skills/ad-script/finalize_storyboard.py "<作品根>" --master 30s --json "<作品根>/脚本/镜头时长.json"
   ```
   对账分镜总时长≈主片目标（超/欠都报）、VO 不被截断、接缝有 transition。0 block 才推进 `ad-image`。

## 广告专有强化

- **《广告法》违禁词硬闸门**（差异化核心）：`ad_law_check.py` 内置绝对化用语/医疗保健极限词/虚假承诺/迷信/促销欺诈词库 + 白名单降噪（最后/最初/第一时间…不误杀），带 pytest。命中 block 退出码非零。
- **总时长是硬约束**：广告 30s 就得 30s，`finalize_storyboard.py` 对账超/欠（n2d 没有这条硬约束）。
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
