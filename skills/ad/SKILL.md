---
name: ad
description: 拍广告 总调度 — 把【客户需求/brief】做成一条 AI 广告片（创意策划→脚本→分镜→角色定妆→场景设计→AI出图→AI视频→配音→剪辑包装→成片）。与 novel2drama(制漫剧)/mv(制MV) 平行的第五条生产线，产物落 拍广告/<项目名>/（成片_主片.mp4 + 多时长 cutdown + 多比例）。**不拆集**（一条主片是整体，可以很长）；多时长/多比例/A·B 走 cutdown 交付件矩阵。**自包含，不复用 n2d-*/mv-* 任何家族 skill**。读 _进度.md 路由到 ad-craft(契约/AI披露) / ad-concept(创意) / ad-script(脚本+分镜+广告法机检) / ad-voice(VO配音) / ad-image(三层定妆+出图) / ad-video(图生视频) / ad-compose(剪辑包装+交付)。换脸用公共 shared-video-faceswap，水印用 shared-watermark。Use when given a 客户需求/brief, a product/brand to advertise, or an existing 拍广告/<项目>/ folder, or asked 拍广告 / 做广告片 / 广告创意 / 广告脚本 / TVC / 信息流广告 / 品牌片 / 产品demo / 带货视频. Triggers 拍广告, 广告片, 广告创意, 广告脚本, 广告分镜, TVC, 信息流广告, 品牌片, 产品demo, 带货视频, 广告成片, ad.
---

# ad — 拍广告生产线 · 总调度

把**一份客户需求（brief）**做成一条 AI 广告片。**输入 = 客户需求/品牌产品**；**产物 = `拍广告/<项目名>/成片_主片.mp4`** + 多时长 cutdown（30→15→6s）+ 多比例（16:9/9:16/1:1）。

这条线几乎覆盖了 写小说(创意/脚本) + 制漫剧(分镜→出图→出视频→配音→合成) 两条线合起来的全套，独有的是**前端创意策划**（策略层）和**后端品牌包装/交付**。

**不拆集铁律**：广告不切「集」。一条主片是一个整体（可以很长）；多时长/多比例/A·B 是**交付件 deliverable**，登记在 `_进度.md` 的「交付版本矩阵」，由 `ad-compose` 重剪/reframe。

**自包含铁律**：`ad-*` 不复用 n2d-*/mv-*/novel-*/song- 任何家族 skill。可借鉴 n2d 的配音先行、两层定妆、契约继承、接缝逻辑，但代码与文档各写各的。换脸调公共 `shared-video-faceswap`，水印调公共 `shared-watermark`。

## 偏好（私有 · 用户选择，不写死在本 skill）

按 `../_偏好约定.md` 读用户私有选择：先读 `<作品根>/_设置.md`；缺则用全局默认 `创作偏好-默认.md` 预填并告知一句；再缺则**首次问一次**→写回 `_设置.md`→同项目沉默沿用。合规/不可逆/花钱多的点（`水印-AI合规标识`、`广告法地区`、`音乐来源`、出图/出视频/合成）每次仍确认。

涉及选择点：`广告类型`、`创意路线`、`基础视觉风格`、`主片时长`、`交付比例`、`cutdown版本`、`生图AI`、`一致性增强`、`生视频AI`、`视频模型路由`、`出视频规格`、`视频分辨率`、`配音后端`、`音乐来源`、`品牌包装模板`、`字幕语言`、`AI视觉使用披露`、`水印-AI合规标识`、`水印-品牌账号`、`广告法地区`、`交付规格`、`生成粒度`、`目标平台`、`发行地区`。

> 作为生产线入口：开新项目（`拍广告/<项目名>/`）时 `python3 skills/ad/scripts/init_project.py "拍广告/<项目名>" --brand <品牌>` 按全局默认初始化 `_设置.md`/`_进度.md`/`需求/brief.json`。

## 作品根约定（不拆集）

```
拍广告/<项目名>/
├── _进度.md / _meta.json / _设置.md
├── 需求/brief.md + brief.json   客户需求结构化（品牌/产品/USP/受众/调性/强制项logo·slogan·法律声明/交付规格）
├── 创意/concept.md + 创意脚本.md  big idea / 主张 / mood&reference / KV方向
├── 脚本/                        广告脚本.md + voiceover.txt + 时间轴.json + storyboard.json + 字幕 + 镜头时长 + 广告法机检报告
├── 设定库/                      global_style + 角色卡 + 场景卡 + 产品卡 + voicemap.json
├── 配音/                        line_NN.wav + vo.wav + 时长清单.json
├── 出图/共享/ 出图/分镜/         三层定妆库（角色/场景/产品）+ 逐镜首尾帧
├── 出视频/分镜/                 每 Clip MP4 + video_model_routes.json
├── 合成/                        成片_主片.mp4 + cutdown/ + 多比例/ + 水印/
├── 合规/                        AI使用说明.md（二期补 compliance_manifest.json）
└── 成片_主片.mp4
```

## 阶段 + 路由

| 阶段 | skill | 产物 | 状态 |
|---|---|---|---|
| 共享契约/立项 | 本调度 + **`ad-craft`** | `_设置.md`+`_进度.md`+`_meta.json`+`需求/brief.json` | ✅ |
| 客户需求 brief | 本调度 | `需求/brief.md`+`brief.json`（结构化客户需求） | ✅ |
| 创意策划 | **`ad-concept`** | `创意/concept.md`+`创意脚本.md` | ✅ |
| 广告脚本+VO+时间轴 | **`ad-script`** | `脚本/广告脚本.md`+`voiceover.txt`+`时间轴.json`+**广告法机检** | ✅ |
| VO配音 | **`ad-voice`** | `配音/时长清单.json`（驱动镜头时长） | ✅ |
| 分镜（实测时长） | **`ad-script`** | `storyboard.json`+`镜头时长.json`+字幕 | ✅ |
| 三层定妆库+出图 | **`ad-image`** | 角色/场景/**产品**定妆 + 逐镜首尾帧 PNG | ✅ |
| 图生视频 | **`ad-video`** | Clip MP4 + 契约继承机检 + 模型路由 | ✅ |
| 剪辑包装+交付 | **`ad-compose`** | 成片 + 品牌包装 end card + cutdown + 多比例 + 交付规格 + 水印 | ✅ |
| 质检/自审(横切) | **`ad-review`** | 双模 QA：产品一致性/品牌色/logo/字幕/音画/违禁词 + 流程自审 | ⏳ 二期 |
| AI披露/交付 | **`ad-craft`** | `合规/AI使用说明.md` | ✅ |

| 用户输入 | 路由到 |
|---|---|
| 有客户需求/品牌产品，要立项拍广告 | 本调度 `init_project.py` 建 `拍广告/<项目>/`，把需求填进 `brief.json` |
| 要做创意/big idea/创意脚本 | `ad-concept` |
| 要写广告脚本/分镜/查广告法违禁词 | `ad-script`（配音前=脚本 pass，配音后=分镜 pass）|
| 要配 VO/旁白 | `ad-voice` |
| 要出定妆/产品图/分镜图 | `ad-image`（三层定妆库：角色/场景/产品）|
| 要图生视频 | `ad-video` |
| 素材齐了要剪辑包装/出 cutdown/多比例/交付 | `ad-compose` |
| 要给画面换脸 | 公共 `shared-video-faceswap`（先过其合规闸门）|
| 要打 AI 标识/品牌水印 | 公共 `shared-watermark` |
| 给了 `拍广告/<项目>/` 没说动作 | `python3 skills/ad/scripts/route.py "<作品根>"` 报进度 + 建议下一步 |

> 推荐顺序：**brief → ad-concept 创意 → ad-script 脚本(过广告法机检) → ad-voice VO → ad-script 分镜 → ad-image 三层定妆+出图 → ad-video 图生视频 → ad-compose 剪辑包装+cutdown+交付 → AI披露/质检**。
> **音频先行**：VO 实测时长驱动镜头时长，`ad-script` 跑两遍（脚本→配音后分镜），与 n2d 同构。广告常是「音乐床 + VO」混合驱动，音乐床作节奏锚一并记录。

## 广告专有强化点（相对 n2d/mv）

- **客户需求 brief 是 source**：替换小说源文本，结构化进 `brief.json`（品牌/产品/USP/受众/调性/强制项/claims/交付规格）。
- **创意策划层**：novel 没有的策略层；big idea / 一句话主张 / mood&reference / KV 方向（`ad-concept`）。
- **《广告法》违禁词机检（硬闸门）**：绝对化用语「最/第一/国家级」、虚假宣传、医疗保健极限词 → `ad-script/ad_law_check.py` 命中即 block。
- **产品定妆（三层定妆库第三层）**：hero product 包装/logo/品牌色跨镜零漂移，是最严格的"角色"。
- **品牌包装 + 交付**：片尾 end card（logo+slogan+CTA）、cutdown 多时长、多比例 reframe、交付规格（响度 LUFS/安全框）。

## 合法性
- 广告 claim（功效/对比/数据）须有依据；绝对化用语等违禁词由 `ad-script` 机检拦截。
- 代言人肖像/真人声音/授权音乐/商业字体需可追溯授权；未授权不投放。换脸走 `shared-video-faceswap` 合规闸门，AI 标识用 `shared-watermark`（只加不去）。

## 与别的线
- **创作线**：`novel-author`(写小说) / `song`(写歌)。**生产线**：`novel2drama`(制漫剧) / `mv`(制MV) / **`ad`(拍广告)**。
- 各线**互不依赖**（自包含）；换脸/水印是公共 `shared-*`。

## 持续改进
工艺/翻车 → 写进对应 ad-* skill 的 `references/`。**新增/改 ad-* skill 后同步更新 `skills/README.md` + `AGENTS.md`/`GEMINI.md` 路由表 + `_偏好约定.md` 选择点目录。**

## 常见错误

| 错误 | 纠正 |
|---|---|
| 把广告拆成「集」 | 不拆集；多时长/多比例走 cutdown 交付件矩阵 |
| 脚本写绝对化用语「最/第一/国家级」 | `ad-script` 广告法机检会 block；改合规表述并留 claim 依据 |
| 产品包装/logo 跨镜漂移 | 产品定妆当最严格"角色"，进三层定妆库 + 逐镜锁 PROD_xx |
| 跳过创意策划直接出图 | 先 `ad-concept` 定 big idea/主张，再脚本分镜，别无脑批量生成 |
| 投放前不打 AI 标识/不留授权痕 | 交付前必过 `shared-watermark` AI 标识 + `ad-craft` AI使用披露 |
