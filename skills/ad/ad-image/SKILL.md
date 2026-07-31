---
name: ad-image
description: 拍广告 第5阶段·三层定妆库 + AI出图 — 建角色/场景/hero product 共享定妆并逐镜出首尾帧；每个 job 分列具体生图模型与访问渠道、真实参考输入和输出。默认 GPT Image 2 via Codex CLI；非默认官方路线需项目签核，逆向路径永久阻断。Use when asked 广告出图/定妆/产品定妆/品牌色/出图prompt/分镜图/KV for a 拍广告 project. Triggers 广告出图, 定妆, 产品定妆, 品牌色, KV, 出图, 出图prompt, 分镜图, 首帧, 尾帧, ad-image.
---

# ad-image — 拍广告 · 三层定妆库 + 出图

广告出图使用**三层定妆库**：
1. **角色定妆**（代言人/模特/虚拟人）——标准三视图（正/侧/背）。
2. **场景定妆**——关键场景多视图。
3. **产品定妆（hero product）**——广告独有、最严：包装/logo/品牌色/材质跨镜**零漂移**，是最严格的"角色"。

然后按 `storyboard.json` 逐镜出**首帧**（+ 标了 `need_end_frame` 的接缝出**尾帧** `镜头N_end.png`）。视觉契约（品牌色 HEX/光位锚/构图）烤进首帧像素。

三层定妆、产品一致性、尾帧接力和机检都落成 ad 自己的 references。

## 偏好（私有）

按 `../skills/ad/ad-craft/references/选择点与偏好.md` 读 `<作品根>/_设置.md`。涉及：`生图模型`、`生图渠道`、`一致性增强`、`基础视觉风格`、`交付比例`、`生成粒度`、`重抽预算策略`。出图是**花钱/高风险**阶段，正式跑前确认具体模型+渠道；旧 `生图AI` 必须迁移。brief 的 claim 分型依据/rights/legal_lines 及分镜 claim 披露此时必须闭合。

## 产品落档机检 product_qc（**gate spend 的硬闸**）

出完一批图、还没继续出视频时跑 `scripts/product_qc.py`——把产品/logo/品牌色漂移（广告线的"脸漂"）在最便宜的点机检拦下，避免漂着出视频再返工烧钱：

```bash
python3 skills/ad/ad-image/scripts/product_qc.py "<作品根>/出图/分镜" [--storyboard PATH] [--strict] [--no-vlm]
```

**逐图即时 QC（ad 线自维护）**：每生成并落档 1 张定妆、首帧或尾帧 PNG，先跑广告线自己的最小 QC，再继续下一张。产品/KV/品牌露出/代言人关键镜必须立即跑 `product_qc.py`（当前脚本以阶段目录全量扫描为主，就全量跑一次并重点处理新图 finding）；普通痛点/空镜也要做 ad-image 本线落档自检（PNG 有效、主比例/安全框、是否有不该出现的 logo/文字/产品变形、是否符合 storyboard 资产声明），并在生产事件或返修记录中留痕。`summary.block>0` 或关键镜未能确认时先重抽/改 prompt/补产品参考，不把坏图传给 `ad-video`。不得抽成公共实现，也不得复用其它系列的 QC 脚本。

增强后的落档检（自包含；缺 Pillow/numpy 优雅降级，只跑结构化/prompt-lint 并在报告标降级）：
1. **prompt-lint（HARD BLOCK，无 Pillow 也跑）**：每个产品镜（`storyboard.assets` 标 `PROD_*: true`，或镜头语义含 App/UI/包装/logo/品牌/CTA/end card）的 `出图/分镜/prompt/镜头N.md` 必须有 参考图/资产引用块 + 结构化 `PROD_*` 资产 ID + 身份锁定句 + 负向(不要改包装文字 / 不要变形 logo)。缺任一 → block。把"绝不文生图产品"从散文落成机检硬约束。
2. **产品语义镜逃逸拦截**：即使 storyboard 忘了写 assets，只要镜头语义含 App/UI/包装/logo/品牌/CTA/end card，也纳入产品 QC；缺 `PROD_*` 资产 ID → block。
3. **asset_registry 对账**：优先读 `出图/共享/asset_registry.json` / `设定库/asset_registry.json`。产品镜建议同时绑定 `PROD_*` 与 `BRAND_*`；缺 registry 或缺品牌资产先 warn，避免出图前没有 logo mask/品牌色/包装禁漂项。
4. **文字可读性**：品牌/UI/CTA/法律文字镜必须在 prompt 写清“文字清晰可读/不乱码/保留原文”；缺锁定句 → warn，缺 prompt → block。
5. **跨比例构图余量**：`safe_area.core_in_center_4x4` 只是内部中心裁切风险提示；缺失或 false → warn。它不能证明抖音/TikTok/Reels 等实际 placement 安全，发布前仍须当前模板 + 具名人审。
6. **产品 ROI 粗定位**：先用定妆参考模板 × 多尺度 NCC 在出图帧里定位产品区域（`locate_product_roi`，峰值 < 0.60 宁可不给框）；定位成功后 6-8 三项按产品区域口径跑，失败则维持整图降级口径并落 `product_roi` finding（定位失败本身就是"产品疑缺席/严重变形"的 warn 信号）。
7. **brand-color ΔE**：有产品 ROI 时严重偏色（ΔE>block 阈）**可 block**；无 ROI 时只作 WARN 启发式，不能因整图环境色不同就宣判品牌不一致。
8. **product dHash 离群**：全组产品镜都有 ROI 时按产品区域口径判（仍 warn·启发式）；否则全帧 Hamming 只作 WARN 候选，不把换构图误判成产品漂移硬挡。
9. **logo 多尺度 NCC**：0.6-1.5 五档尺度取峰值，有 ROI 时窗内搜索（假峰更少、口径更强）；只作 WARN 快筛，Logo/包装文字硬签收来自真实参考输入、可控后期层和人工并排复核。
10. **VLM 并排裁决接线（默认开启，`--no-vlm` 关）**：run_qc 自动刷新 `生产数据/ad_vlm_judge_tasks.json`（每产品镜 × PROD_/BRAND_ 资产一条「出图帧 vs 定妆参考」任务，sha256 绑定），并把 `ad_vlm_judge_verdicts.json` 里的有效裁决折进 findings——suspect/低分 → warn；任务包有任务但 0 裁决 → `vlm_product_unadjudicated` warn（机检空转要可见）；部分裁决 → `vlm_product_partial_coverage` warn。裁决由多模态 agent 逐条看图打分回填（合同细节见 `scripts/product_vlm_judge.py` 文件头），这是唯一"看图判产品长对没有"的内容级检，ΔE/dHash/NCC 抓不住的形态错误靠它。
11. **禁本地贴图伪修复**：若 `生产数据/production_events.jsonl` 记录某最终产品镜来自 `local_product_patch` / `logo_patch` / `packaging_patch` / alpha blend / pasteback 等 image-stage 局部贴图链路，直接 block。真 logo/包装文字贴图应在 `ad-compose` 交付层做，不得拿来伪造出图阶段产品一致性通过。

报告写 **`出图/分镜/product_qc.json`**，schema `{"kind":"ad_product_qc","version":2,"summary":{"block":N,"warn":N,"info":N},"findings":[{"severity","shot","check","reason","detail"}],"qc_environment":{"precision_level","pending_product_images",...}}`；`summary.block>0` → 退出非零。`ad-craft/gate.py` 读 `summary.block`、`qc_environment.precision_level` 和 `pending_product_images` 据此挡 spend（与 `video_contract_findings` 读 `contract_inheritance.json` 同形）。`--strict` 给 `ad-review`/刷新用：降级 info 提级 warn 进候选重出。测试：`cd skills/ad/ad-image/scripts && python3 -m pytest test_plan_prompts.py test_product_qc.py test_plan_cover.py`。

## 生图后端治理

默认路线是 **生图模型=GPT Image 2，生图渠道=Codex CLI**（也可用官方 OpenAI Images API）。Seedream 4.5、Nano Banana Pro、Kling Image 3.0、Sora 2 或其它**自定义模型**（含具名 Dreamina Image 官方版本）只能作为用户明确签核的单项目例外，逆向 Dreamina/即梦路径仍禁用；签核写 `<作品根>/合规/image_backend_override.json`。永久硬闸：① manifest 每个 job 必须分别落 `model/channel`，不能只写厂商壳/backend；② 项目内不混用路线；③ 禁第三方逆向/未授权出图。视频渠道不改变图片路线。

**付费渲染资金安全**（签核例外走 `scripts/render_dreamina.py` 时）：① 提交成功即**先落盘** `submit_id`/结果地址再下载——下载失败重跑走免费取回，绝不因网络抖动二次付费；② job 账本原子写（同目录 tmp+rename），中断不烂账；③ 下载/查询类幂等操作有限重试+退避，付费提交**永不自动重试**；④ `--max-credits N` 预算封顶，累计消耗到顶即停并列出未跑 job；⑤ `--limit` 按条数截断小步验证。

## 工作流

0. **生成出图 prompt 包**（付费生图前的可复跑计划）：
   ```bash
   python3 skills/ad/ad-image/scripts/plan_prompts.py "<作品根>"
   ```
   产物：`出图/共享/asset_registry.json`、共享/逐镜 prompt 和 `image_jobs_manifest.json`。产品 job 写 `reference_inputs` / `requires_image_input` / prompt hash；正式 runner 必须把真实参考图传给 image-to-image API，并记录 `actual_reference_inputs`，否则 gate 阻断。每个 job 还落 **`planned_seed`**（同一主资产跨镜同 seed、项目名+资产 ID 确定性派生，重抽单镜不引入新随机源）与 **`seed_capability`**（适配层三态：后端支持才真传 seed，unknown/unavailable 如实标注不假装生效）——无主体库路线下固定 seed 是少数能稳住跨镜产品/代言人的廉价锚。
1. **建三层定妆库**（`出图/共享/`）：
   - 角色：每个出正/侧/背三视图 → `定妆_<角色>_三视图.png`。
   - 场景：关键场景四视图。
   3. **产品**：包装正/侧/背 + 关键细节（logo 特写、材质）→ `定妆_<产品>.png`，并在 `出图/共享/asset_registry.json` 登记 `PROD_*`/`BRAND_*`、品牌 HEX、logo mask/保护区、包装文字禁改项、UI 状态。
   - **多视图分参考**：定妆是网格大图（master sheet）时，用 `scripts/derive_reference_views.py --grid/--box` 裁成逐视图分参考 PNG（`出图/共享/定妆视图/<资产>/`）并落 `生产数据/ad_reference_views.json` 溯源（source sha256+裁切框）；把 `suggested_registry_patch` 里的路径**手工**补进 asset_registry 的 `reference_images` 再刷新快照——单张定妆照对 AI 只是固定板式，`reference_planner` 处方要求的多张参考就从这里来。
      - **品牌色锁 (Hex-Lock)**：显式声明品牌 HEX 值，并在 Prompt 末尾追加 `color consistency: strict HEX #[value]`。
      - **Logo 保护区**：标记 Logo 坐标，禁止 AI 在 Logo 区域生成环境干扰（如遮挡、强反光）。
   2. **写视觉契约总览**（`出图/分镜/prompt/00_总览.md`）：继承 `storyboard.json.visual_contract`（品牌色/光位锚/画风/构图），逐镜带视线方向/光位/起幅余量。
   3. **跨比例构图余量对账**：8x8 中心网格只为多画幅裁切预留边缘；不得把它写成平台官方安全区或最终通过证据。

4. **逐图落档 QC**：每张定妆/首帧/尾帧 PNG 落档后立即跑上节的 ad-image QC；产品/KV/代言人/品牌镜先过 `product_qc.py`，普通镜至少完成本线落档自检并记录。单张不过先修单张，不继续批量出后续图。只有 prompt 包而无 PNG 时，`product_qc.py` 只能证明 prompt-lint 通过，不能放行出视频。
5. **批次/全片收尾 QC**：一批或全部分镜出完后再跑一次 `product_qc.py`，确认报告时间晚于所有关键 PNG，`summary.block==0` 且无待确认关键镜后才进入 `ad-video`。
6. 回写 `_进度.md` 出图 ✅：`python3 skills/ad/ad-craft/scripts/progress_set.py set-stage "<作品根>" image --status ✅ --artifact 出图/分镜`，提示 `ad-video`。

## 作品封面（竖版 key visual / endcard）

作品卡片要一张**竖版 9:16** key visual / endcard 作封面，落 `_meta.json.cover`（作品根相对路径）。这是「一图讲清这条广告在卖什么」的门面，不是分镜首帧；产物与分镜分目录，落 `出图/封面/`。

```bash
python3 skills/ad/ad-image/scripts/plan_cover.py "<作品根>"      # 出封面 prompt/job 包（不渲染 PNG）
# 外部渲染竖版 PNG → 出图/封面/cover.png 后，确定性回填：
python3 skills/ad/ad-craft/scripts/meta_card.py cover "<作品根>" --png 出图/封面/cover.png
```

- **优雅降级（C4/B4）**：`plan_cover.py` 只产 `出图/封面/封面_prompt.md` + `出图/封面/cover_job.json` + 生产事件留痕；纯净机（断网/无凭证）也能一路产出封面 job 包并讲清缺什么，`_meta.json.cover` 保持 `null`，绝不伪造 PNG。
- **回填 helper**：`meta_card.py cover` 校验 PNG 在作品根内、存在、`.png`、竖版（Pillow 可用时判 `h≥w`，缺 Pillow 优雅跳过尺寸校验），通过才写 `cover`，并在 `_进度.md` 维护记录留痕（B5）；非竖版/越界/缺文件一律拒写、不阻断其它阶段。作废封面用 `meta_card.py clear-cover`。
- **具体模型（C5）**：封面「由什么生成」落到 `生图模型`（默认 GPT Image 2），`生图渠道`（默认 Codex CLI）作访问入口**分列**；封面与分镜同走生图后端治理，逆向/未授权路径同禁。
- **身份零漂移**：封面复用三层定妆库的品牌/hero product 身份锁（品牌色 HEX / logo / 包装文字），有 `PROD_*`/`BRAND_*` 资产时必须 image2image 引用真实定妆图，不纯文生图。

> **简介（synopsis）**：作品卡片的一段简介来自 `_meta.json.synopsis`（≤240 字），由 `ad` 立项写占位、brief 产出后 `python3 skills/ad/ad-craft/scripts/meta_card.py synopsis "<作品根>"` 确定性回填 brief 的 `key_message`（不覆盖用户手写内容）。

## 广告专有强化

- **产品定妆 = 最严一致性**：包装文字/logo/品牌色/比例不能漂。绝不文生图产品（必 image2image + 产品参考图）。品牌色锁 HEX，logo 锁位置与最小留白。
- **品牌色锁**：`visual_contract.品牌色` 是硬约束，逐镜 prompt 带品牌主色，避免环境光把品牌色染偏。
- **KV 对齐**：`ad-concept` 的 KV 方向是主视觉锚，定妆库与关键镜要对住 KV。
- **多比例不重复出图**：按 `交付比例` 主比例出图，其它比例 `ad-compose` reframe（留够安全框余量，构图别贴边）。

## 一致性梯子（出图）
①参考图派生（默认）→ ②后端原生主体ID/主体库（Seedream/可灵/Sora Cameo·opt-in）→ ③LoRA（仅核心长线代言人）。锚点句（锁特征词）+ 身份锁定句（锁"同一张脸/同一个包装"）叠加用。产品/logo 用后端原生主体库或多参考最稳。

梯子不再只是散文：档位真值在 **`skills/ad/_lib/image_backend_adapter.py`**，与 `_设置.md` 的
`一致性增强` 四档（共享定妆+锚点 | 指定参考图 | 后端主体库 | +LoRA）一一对齐。后端按 **能力**登记
（与 `ad-video/scripts/route.py` 同哲学：问能力不问品牌，换厂只改能力表）。能力是**三态**——
厂商无公开证据的一律 `unknown`，`has_capability()` 只认 available，**未知绝不当作支持**；未知后端回退保守
profile（只有 reference、参考预算 1）。默认路线 GPT Image 2 via Codex **无持久主体库**，梯子真实封顶在
「指定参考图」档——想上第②档必须换后端并签核。

### 逐镜参考处方（事前·出图前跑）

```bash
python3 skills/ad/ad-image/scripts/reference_planner.py "<作品根>" --write
```

治的根因：单张定妆照对 AI 只是个"固定板式"，身份判别细节不足；换景别/角度/光线/表情时模型会重画，
逐镜累积成漂移。此前 `plan_prompts.reference_paths()` 只是把 registry 里**静态登记**的 `reference_images`
原样列出，**不看镜头变化量、不看后端能力**。规划器逐镜逐资产算变化量 delta × 后端能力，开出"这镜喂哪些参考 +
要不要控制网 + 要不要升档"，产 `生产数据/ad_reference_plan.{json,md}`。**产品/品牌资产按最严格的"角色"加权**
（`PROD_*`/`BRAND_*` 漂了整片报废），产品镜单参考会告警。两个补充因子：① **复现间隔 gap**——按镜序算每资产
距上次出现隔了几镜（产品/品牌 ≥3 镜、一般资产 ≥4 镜即长间隔复现），触发时参考下限 +1 并把**最早定妆锚**
置顶重注入，治"隔了半条片子再登场就漂"的复现衰减；② **升档可达路由建议**——建议档超出当前后端能力时
不止说"够不着"，还列出能力表里够得着该档的具体后端（模型+渠道）供切镜参考（advisory，换后端须按治理规矩签核）。

与 `product_qc` 的关系是**互补**，不是替代：`reference_planner` 是**事前处方**（还没花钱），`product_qc` 是
**事后诊断**（图已生成）。gate 在 `--stage image` 以 **advisory** 并入（缺报告只 info、报告里的 block 降为
warn）——创意/启发式不硬挡付费的规矩见 `gate.py` 的 `score_findings`。

### 打样矩阵（事前·全量出图前跑）

```bash
python3 skills/ad/ad-image/scripts/pilot_matrix.py "<作品根>" --write
```

传统 PPM「先看小样再开机」纪律的机检化：全量批次前从分镜挑 **2-5 镜代表样**
先出先人审，覆盖五轴——`hook`（首镜·被看最多的画面）/ `product_hero`（产品还原：品牌色 ΔE/logo/质感）/
`risk_max`（`ad_reference_plan` delta_score 最高镜，缺报告退化为资产最多镜）/ `text_render`（文字板/endcard：
AI 已知弱项，查错别字/字形崩坏）/ `multi_entity`（人+产品同框：比例/构图串染）。一镜可覆盖多轴（择最少镜
覆盖最多轴），某轴无候选如实报 `absent` 不臆造。产 `生产数据/ad_pilot_matrix.{json,md}`，逐镜给中文理由 +
审看焦点清单。纯计划零花钱、advisory（gate `--stage image` 同 advisory 接法），打不打样由人定。

### 产品漂移风险账本（事前·2026-07 第七轮）

```bash
python3 skills/ad/ad-image/scripts/product_drift_risk.py "<作品根>" --write
```

reference_planner 开处方（每镜喂什么参考）、product_qc 事后诊断之间缺的一层：**出图前把
逐镜漂移风险打分排序**。分数来源：处方 delta_score 复用 + 分镜词面风险信号（产品特写/微距 +14、
包装文字渲染 +12、透明反光材质 +10、极端角度 +8、人+产品同框 +10、场景首现 +6、资产未登记
参考 +18）+ **实测回灌**（product_qc 已报 warn/block 的镜直升 high，不臆造）。≥40 分为 high；
high 镜不在 `ad_pilot_matrix` 打样集 → warn `high_risk_unpiloted`（高危镜没打样就全量=最贵翻车
路径）。产 `生产数据/ad_product_drift_risk.{json,md}`，advisory·block 恒 0，gate image 侧车。

## 重抽预算策略（两档）

图片重抽只保留两档：`预算充足` / `预算一般`，默认 `预算充足`。旧值 `预算不足` / `预算不够` 一律归并为 `预算一般`。这里的“满意”以本张图的落档自检 + 用户/制作判断为准，每次重抽都必须记录事件、保留候选或废料，不设固定次数上限。

| 策略 | 关键图片（产品/KV/代言人/品牌镜） | 普通镜 | 终止 |
|---|---|---|---|
| **预算充足**（默认） | 严格自检，产品/logo/品牌色/代言人脸零漂移容忍；不满意就继续重抽/改 prompt/换参考，直到满意落档 | 同样严格自检；普通镜也不将就，直到满意落档 | 满意为止 |
| **预算一般** | **只关键图片严格自检**；产品 hero、KV、封面候选、卖点特写、代言人/主模特 CU 不满意就继续重抽/改 prompt/换参考，直到满意落档 | 普通镜走筛选宽容：无核心错位、无产品/logo/品牌色硬伤、无合规禁忌即可落档，不追小瑕疵 | 关键图满意；普通图可用 |

**关键图片判定**：产品定妆、包装/logo/材质细节、KV 主视觉、首镜/尾镜、封面候选、卖点特写、强品牌露出、代言人/主模特 CU/ECU、需要尾帧接力的连续动作镜、多比例 reframe 会反复引用的安全框基准图。

## 常见错误

| 错误 | 纠正 |
|---|---|
| 文生图产品（包装/logo 全靠描述） | 必 image2image + 产品定妆参考；文生图必漂 |
| 品牌色被环境光染偏 | 锁 `visual_contract.品牌色` HEX，逐镜 prompt 带品牌主色 |
| 每个交付比例都重新出图 | 按主比例出图，其它比例 ad-compose reframe，构图留安全框 |
| 项目内混用生图后端 | 一个项目锁一个后端；切换要记录并重出受影响图 |
| logo 摆错位/被裁 | 产品 checklist 锁 logo 位置与最小留白 |
| 把 `预算一般` 当成广告产品图也能差不多 | 错。产品/KV/代言人/品牌露出都属于关键图片，预算一般也要严格自检直到满意 |
| 出完一批才发现产品/logo 漂 | 违反逐图即时 QC；每张产品/KV/品牌镜落档后立刻跑 ad-image 的 `product_qc.py`，不过先修当前图 |
