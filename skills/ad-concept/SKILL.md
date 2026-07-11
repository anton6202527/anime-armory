---
name: ad-concept
description: 拍广告 第1阶段·创意策划 — 把 需求/brief.json（客户需求）转成创意：big idea / 一句话主张(key message) / 创意路线(功能卖点·情感·幽默·悬念·种草) / mood&reference / KV(key visual) 方向 / 故事线。产 创意/concept.md + 创意脚本.md，交给 ad-script 写脚本。ad-* 自包含。Use when starting a 拍广告 project's creative, or asked 广告创意 / big idea / 创意策划 / 一句话主张 / 创意脚本 / mood board. Triggers 广告创意, 创意策划, big idea, 大创意, 一句话主张, key message, 创意路线, KV方向, 创意脚本, ad-concept.
---

# ad-concept — 拍广告 · 创意策划（策略层）

把**客户需求 brief** 转成**创意**。广告创意先定 big idea 和一句话主张，再进入脚本分镜。**自身只产创意文档，不写分拆镜头脚本**（那是 `ad-script`）。

**输入**：`需求/brief.json` + `brief.md`（若还没填全，先访谈式补齐）。
**产物**：`创意/concept.md`（big idea/主张/路线/mood&reference/KV方向/故事线）+ `创意/创意脚本.md`（creative treatment：一段式叙述创意如何展开，给 ad-script 拆镜头用）。

## 偏好（私有）

按 `../skills/ad-craft/references/选择点与偏好.md` 读 `<作品根>/_设置.md`。涉及：`广告类型`、`广告目标`、`漏斗阶段`、`创意路线`、`基础视觉风格`、`主片时长`、`目标平台`。

## 工作流

### 第0步：brief 补齐（AI 代理交互节点 · 三层访谈，别问一面墙）
读 `需求/brief.json`，缺项按三层分治。**别让用户填 JSON**——AI 问人话、自己落档：

1. **必问最小集**：brand / product / usp / audience / `campaign_objective`。目标至少落到品牌认知、考虑种草、转化行动或全链路之一。
2. **推断 + 一次确认**：漏斗阶段、调性、key message、时长、平台、路线；同时确认 offer、landing page（如有）。
3. **花钱前闭合**：claims、rights、legal_lines、`measurement.primary_kpi`、`measurement.conversion_event`。claim 不能只写“有据”，须准备证据文件、方法、日期、适用地区、批准人给 producer pack。

补完把答案结构化回写 `brief.json` + 人读 `brief.md`，并回写 `_进度.md` 客户需求立项 ✅。

### 第1步：定 big idea 与一句话主张
- 先写 **Objective → Audience → Promise → Proof → Action**：目标/KPI 不同，品牌露出、产品演示和 CTA 比重也不同。
- **big idea**：一句能统领整片的核心创意（不是卖点罗列，是"用什么角度让人记住"）。
- **一句话主张 key message**：观众看完该记住的一句话（常与 slogan 呼应，但不等于 slogan）。
- 给 2–3 个候选，按 brief 的受众/调性/平台推荐一个，让用户选。

### 第2步：定创意路线 + mood & reference
- `创意路线`：功能卖点 / 情感共鸣 / 幽默 / 悬念反转 / 名人代言 / 场景种草（见 `references/creative_frameworks.md`）。
- **mood & reference**：画面气质参考（光色/质感/节奏/参考片描述，**不抄袭具体作品**），写进 concept。
- **KV(key visual) 方向**：主视觉的构图/主体/品牌色/产品位，给 `ad-image` 的定妆库当锚。

### 第3步：故事线 + 时长结构
按 `主片时长` 给**段落级故事线**（不是逐镜头）：黄金 3 秒钩子 → 痛点/情境 → 产品/方案 → 证据/记忆点 → CTA/品牌包装。每段给秒数预算（给 ad-script 当时间轴种子）。

### 第4步：落档 + 推进
写 `创意/concept.md` + `创意/创意脚本.md`，回写 `_进度.md` 创意策划 ✅，提示下一步 `ad-script`。

## concept.md 结构（建议）

```markdown
# 创意 — <项目名>
## big idea
## 一句话主张 (key message)
## 创意路线         # 功能卖点/情感/幽默/悬念/种草 + 为什么选它
## mood & reference  # 气质/光色/质感/节奏；参考描述（不抄具体片）
## KV 方向           # 主视觉：主体/构图/品牌色/产品位/slogan 摆位
## 故事线（段落级）   # 钩子→痛点→方案→证据→CTA，每段秒数预算
## 强制项 mandatories # logo/slogan/法律声明/endcard CTA（来自 brief）
## 衡量设计           # campaign objective / primary KPI / conversion event / variant hypothesis
## 必避点            # 竞品/违禁表述/品牌禁忌（来自 brief）
```

## 广告专有要点

- **先策略后执行**：没有 big idea 别急着拆镜头。一句话主张要能落到 KV 和片尾。
- **claims 要可证**：功效/对比/数据类主张在 concept 阶段就标"需依据"，下游 `ad-script` 广告法机检会拦绝对化用语。
- **强制项前置**：logo/slogan/法律声明/CTA 是 brief 的硬约束，concept 就写清，`ad-compose` 片尾包装据此做 end card。

## 常见错误

| 错误 | 纠正 |
|---|---|
| 把卖点罗列当 big idea | big idea 是统领角度，不是 feature list |
| 跳过 brief 直接发想 | 先把客户需求补齐结构化，创意要对住受众/调性/强制项 |
| mood 抄袭具体爆款广告 | 只描述气质/光色/节奏，不复制他人作品的具体表达 |
| 让用户自己填 brief.json | AI 访谈问人话→自己落 JSON（Interactive Flow） |
