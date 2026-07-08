---
name: ad-image
description: 拍广告 第5阶段·三层定妆库 + AI出图 — 为广告片建共享定妆库（角色/代言人 + 场景 + **产品定妆 hero product**：包装/logo/品牌色跨镜零漂移），再按 storyboard.json 逐镜出首帧/尾帧 PNG。视觉契约（品牌色/光位/构图）烤进首帧。生图AI 是选择点（默认 Codex），放行官方多参考后端（Seedream/可灵主体库/Nano Banana/Sora Cameo），拦项目内后端混用 + 逆向出图。Use when asked 广告出图/定妆/产品定妆/品牌色/出图prompt/分镜图/KV for a 拍广告 project. Triggers 广告出图, 定妆, 产品定妆, 品牌色, KV, 出图, 出图prompt, 分镜图, 首帧, 尾帧, ad-image.
---

# ad-image — 拍广告 · 三层定妆库 + 出图

广告出图使用**三层定妆库**：
1. **角色定妆**（代言人/模特/虚拟人）——标准三视图（正/侧/背）。
2. **场景定妆**——关键场景多视图。
3. **产品定妆（hero product）**——广告独有、最严：包装/logo/品牌色/材质跨镜**零漂移**，是最严格的"角色"。

然后按 `storyboard.json` 逐镜出**首帧**（+ 标了 `need_end_frame` 的接缝出**尾帧** `镜头N_end.png`）。视觉契约（品牌色 HEX/光位锚/构图）烤进首帧像素。

三层定妆、产品一致性、尾帧接力和机检都落成 ad 自己的 references。

## 偏好（私有）

按 `../skills/ad-craft/references/选择点与偏好.md` 读 `<作品根>/_设置.md`。涉及：`生图AI`、`一致性增强`、`基础视觉风格`、`交付比例`（出图按主比例，cutdown 比例由 `ad-compose` reframe，不重复出图）、`生成粒度`、`重抽预算策略`。出图是**花钱/高风险**阶段，正式跑前确认；同时 brief 的可延后合规项（claims 依据/rights 授权/legal_lines）此时必须补齐——正式生产前跑 `python3 skills/ad-craft/scripts/gate.py "<作品根>" --stage image`，有 block 先回 `ad-concept`/`ad-script` 补齐。

## 产品落档机检 product_qc（**gate spend 的硬闸**）

出完一批图、还没继续出视频时跑 `scripts/product_qc.py`——把产品/logo/品牌色漂移（广告线的"脸漂"）在最便宜的点机检拦下，避免漂着出视频再返工烧钱：

```bash
python3 skills/ad-image/scripts/product_qc.py "<作品根>/出图/分镜" [--storyboard PATH] [--strict]
```

**逐图即时 QC（ad 线自维护）**：每生成并落档 1 张定妆、首帧或尾帧 PNG，先跑广告线自己的最小 QC，再继续下一张。产品/KV/品牌露出/代言人关键镜必须立即跑 `product_qc.py`（当前脚本以阶段目录全量扫描为主，就全量跑一次并重点处理新图 finding）；普通痛点/空镜也要做 ad-image 本线落档自检（PNG 有效、主比例/安全框、是否有不该出现的 logo/文字/产品变形、是否符合 storyboard 资产声明），并在生产事件或返修记录中留痕。`summary.block>0` 或关键镜未能确认时先重抽/改 prompt/补产品参考，不把坏图传给 `ad-video`。不得抽成公共实现，也不得复用其它系列的 QC 脚本。

增强后的落档检（自包含；缺 Pillow/numpy 优雅降级，只跑结构化/prompt-lint 并在报告标降级）：
1. **prompt-lint（HARD BLOCK，无 Pillow 也跑）**：每个产品镜（`storyboard.assets` 标 `PROD_*: true`，或镜头语义含 App/UI/包装/logo/品牌/CTA/end card）的 `出图/分镜/prompt/镜头N.md` 必须有 参考图/资产引用块 + 结构化 `PROD_*` 资产 ID + 身份锁定句 + 负向(不要改包装文字 / 不要变形 logo)。缺任一 → block。把"绝不文生图产品"从散文落成机检硬约束。
2. **产品语义镜逃逸拦截**：即使 storyboard 忘了写 assets，只要镜头语义含 App/UI/包装/logo/品牌/CTA/end card，也纳入产品 QC；缺 `PROD_*` 资产 ID → block。
3. **asset_registry 对账**：优先读 `出图/共享/asset_registry.json` / `设定库/asset_registry.json`。产品镜建议同时绑定 `PROD_*` 与 `BRAND_*`；缺 registry 或缺品牌资产先 warn，避免出图前没有 logo mask/品牌色/包装禁漂项。
4. **文字可读性**：品牌/UI/CTA/法律文字镜必须在 prompt 写清“文字清晰可读/不乱码/保留原文”；缺锁定句 → warn，缺 prompt → block。
5. **万能安全区**：产品/logo/UI/CTA 镜应写 `safe_area.core_in_center_4x4=true`；显式 false → block，缺声明 → warn。
6. **brand-color ΔE**：产品镜主色 vs `visual_contract.品牌色` HEX（CIE76 Lab）。超阈 → block，临界 → warn；无区域信息取整图主色并降级 warn。
7. **product dHash 离群**：产品镜组内 dHash 最近邻 Hamming 距离离群 → 漂移 warn/block。
8. **logo 模板匹配**：仅当注册了 `出图/共享/定妆库/产品/logo.png` 时做 NCC 粗匹配；缺失/形变 → flag。无模板干净跳过。
9. **禁本地贴图伪修复**：若 `生产数据/production_events.jsonl` 记录某最终产品镜来自 `local_product_patch` / `logo_patch` / `packaging_patch` / alpha blend / pasteback 等 image-stage 局部贴图链路，直接 block。真 logo/包装文字贴图应在 `ad-compose` 交付层做，不得拿来伪造出图阶段产品一致性通过。

报告写 **`出图/分镜/product_qc.json`**，schema `{"kind":"ad_product_qc","version":2,"summary":{"block":N,"warn":N,"info":N},"findings":[{"severity","shot","check","reason","detail"}],"qc_environment":{"precision_level","pending_product_images",...}}`；`summary.block>0` → 退出非零。`ad-craft/gate.py` 读 `summary.block`、`qc_environment.precision_level` 和 `pending_product_images` 据此挡 spend（与 `video_contract_findings` 读 `contract_inheritance.json` 同形）。`--strict` 给 `ad-review`/刷新用：降级 info 提级 warn 进候选重出。测试：`cd skills/ad-image/scripts && python3 -m pytest test_plan_prompts.py test_product_qc.py`。

## 生图后端治理

`生图AI` 默认且优先 **Codex / GPT Image 2**（或官方 OpenAI Images）。非 Codex/OpenAI 的官方后端（Seedream、可灵主体库、Nano Banana、Sora Cameo，含 Dreamina/即梦官方 CLI/API）只能作为用户明确签核的单项目例外；签核写入 `<作品根>/合规/image_backend_override.json` 后，`ad-craft/scripts/gate.py --stage image` 才放行。两条永久硬闸门仍保留：① **项目内不混用后端** ② **禁第三方逆向/未授权出图**（即梦/Dreamina 逆向路径 forbidden）。不得因为本机 `dreamina` 可用、视频阶段走即梦，或为了省事而自动切到即梦生图。

## 工作流

0. **生成出图 prompt 包**（付费生图前的可复跑计划）：
   ```bash
   python3 skills/ad-image/scripts/plan_prompts.py "<作品根>"
   ```
   产物：`出图/共享/asset_registry.json`、`出图/共享/prompt/品牌_*.md`、`出图/共享/prompt/产品_*.md`、`出图/分镜/prompt/00_总览.md`、逐镜 `镜头NN.md` / `镜头NN_end.md`、`出图/分镜/image_jobs_manifest.json`。此脚本只做 prompt 计划和 jobs manifest，不调用生图后端，不伪造 PNG。
1. **建三层定妆库**（`出图/共享/`）：
   - 角色：每个出正/侧/背三视图 → `定妆_<角色>_三视图.png`。
   - 场景：关键场景四视图。
   3. **产品**：包装正/侧/背 + 关键细节（logo 特写、材质）→ `定妆_<产品>.png`，并在 `出图/共享/asset_registry.json` 登记 `PROD_*`/`BRAND_*`、品牌 HEX、logo mask/保护区、包装文字禁改项、UI 状态。
      - **品牌色锁 (Hex-Lock)**：显式声明品牌 HEX 值，并在 Prompt 末尾追加 `color consistency: strict HEX #[value]`。
      - **Logo 保护区**：标记 Logo 坐标，禁止 AI 在 Logo 区域生成环境干扰（如遮挡、强反光）。
   2. **写视觉契约总览**（`出图/分镜/prompt/00_总览.md`）：继承 `storyboard.json.visual_contract`（品牌色/光位锚/画风/构图），逐镜带视线方向/光位/起幅余量。
   3. **万能安全区对账**：出图时，确保核心资产位于 8x8 网格中心，为多画幅裁切预留边缘。

4. **逐图落档 QC**：每张定妆/首帧/尾帧 PNG 落档后立即跑上节的 ad-image QC；产品/KV/代言人/品牌镜先过 `product_qc.py`，普通镜至少完成本线落档自检并记录。单张不过先修单张，不继续批量出后续图。只有 prompt 包而无 PNG 时，`product_qc.py` 只能证明 prompt-lint 通过，不能放行出视频。
5. **批次/全片收尾 QC**：一批或全部分镜出完后再跑一次 `product_qc.py`，确认报告时间晚于所有关键 PNG，`summary.block==0` 且无待确认关键镜后才进入 `ad-video`。
6. 回写 `_进度.md` 出图 ✅：`python3 skills/ad-craft/scripts/progress_set.py set-stage "<作品根>" image --status ✅ --artifact 出图/分镜`，提示 `ad-video`。

## 广告专有强化

- **产品定妆 = 最严一致性**：包装文字/logo/品牌色/比例不能漂。绝不文生图产品（必 image2image + 产品参考图）。品牌色锁 HEX，logo 锁位置与最小留白。
- **品牌色锁**：`visual_contract.品牌色` 是硬约束，逐镜 prompt 带品牌主色，避免环境光把品牌色染偏。
- **KV 对齐**：`ad-concept` 的 KV 方向是主视觉锚，定妆库与关键镜要对住 KV。
- **多比例不重复出图**：按 `交付比例` 主比例出图，其它比例 `ad-compose` reframe（留够安全框余量，构图别贴边）。

## 一致性梯子（出图）
①参考图派生（默认）→ ②后端原生主体ID/主体库（Seedream/可灵/Sora Cameo·opt-in）→ ③LoRA（仅核心长线代言人）。锚点句（锁特征词）+ 身份锁定句（锁"同一张脸/同一个包装"）叠加用。产品/logo 用后端原生主体库或多参考最稳。

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
