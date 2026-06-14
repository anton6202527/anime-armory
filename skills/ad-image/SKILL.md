---
name: ad-image
description: 拍广告 第5阶段·三层定妆库 + AI出图 — 为广告片建共享定妆库（角色/代言人 + 场景 + **产品定妆 hero product**：包装/logo/品牌色跨镜零漂移），再按 storyboard.json 逐镜出首帧/尾帧 PNG。视觉契约（品牌色/光位/构图）烤进首帧。生图AI 是选择点（默认 Codex），放行官方多参考后端（Seedream/可灵主体库/Nano Banana/Sora Cameo），拦项目内后端混用 + 逆向出图。ad-* 自包含，不复用 n2d-image。Use when asked 广告出图/定妆/产品定妆/品牌色/出图prompt/分镜图/KV for a 拍广告 project. Triggers 广告出图, 定妆, 产品定妆, 品牌色, KV, 出图, 出图prompt, 分镜图, 首帧, 尾帧, ad-image.
---

# ad-image — 拍广告 · 三层定妆库 + 出图

两层出图（与 n2d 同构）但定妆库是**三层**：
1. **角色定妆**（代言人/模特/虚拟人）——标准三视图（正/侧/背）。
2. **场景定妆**——关键场景多视图。
3. **产品定妆（hero product）**——广告独有、最严：包装/logo/品牌色/材质跨镜**零漂移**，是最严格的"角色"。

然后按 `storyboard.json` 逐镜出**首帧**（+ 标了 `need_end_frame` 的接缝出**尾帧** `镜头N_end.png`）。视觉契约（品牌色 HEX/光位锚/构图）烤进首帧像素。

**自包含**：不复用 `n2d-image`；借鉴两层出图/一致性梯子/尾帧接力思路，落成 ad 自己的 references。

## 偏好（私有）

按 `../skills/ad-craft/references/选择点与偏好.md` 读 `<作品根>/_设置.md`。涉及：`生图AI`、`一致性增强`、`基础视觉风格`、`交付比例`（出图按主比例，cutdown 比例由 `ad-compose` reframe，不重复出图）、`生成粒度`、`重抽预算策略`。出图是**花钱/高风险**阶段，正式跑前确认；同时 brief 的可延后合规项（claims 依据/rights 授权/legal_lines）此时必须补齐——正式生产前跑 `python3 skills/ad-craft/scripts/gate.py "<作品根>" --stage image`，有 block 先回 `ad-concept`/`ad-script` 补齐。

## 产品落档机检 product_qc（**gate spend 的硬闸**）

出完一批图、还没继续出视频时跑 `scripts/product_qc.py`——把产品/logo/品牌色漂移（广告线的"脸漂"）在最便宜的点机检拦下，避免漂着出视频再返工烧钱：

```bash
python3 skills/ad-image/scripts/product_qc.py "<作品根>/出图/分镜" [--storyboard PATH] [--strict]
```

四项检（自包含，借鉴 `n2d-image/image_qc.py` 架构但不 import n2d；缺 Pillow/numpy 优雅降级，只跑 prompt-lint 并在报告标降级）：
1. **prompt-lint（HARD BLOCK，无 Pillow 也跑）**：每个产品镜（`storyboard.assets` 标 `PROD_*: true`）的 `出图/分镜/prompt/镜头N.md` 必须有 参考图/资产引用块 + 身份锁定句 + 负向(不要改包装文字 / 不要变形 logo)。缺任一 → block。把"绝不文生图产品"从散文落成机检硬约束。
2. **brand-color ΔE**：产品镜主色 vs `visual_contract.品牌色` HEX（CIE76 Lab）。超阈 → block，临界 → warn；无区域信息取整图主色并降级 warn。
3. **product dHash 离群**：产品镜组内 dHash 最近邻 Hamming 距离离群 → 漂移 warn/block。
4. **logo 模板匹配**：仅当注册了 `出图/共享/定妆库/产品/logo.png` 时做 NCC 粗匹配；缺失/形变 → flag。无模板干净跳过。

报告写 **`出图/分镜/product_qc.json`**，schema `{"summary":{"block":N,"warn":N,"info":N},"findings":[{"severity","shot","check","reason","detail"},...]}`；`summary.block>0` → 退出非零。`ad-craft/gate.py` 读 `summary.block` 据此挡 spend（与 `video_contract_findings` 读 `contract_inheritance.json` 同形）。`--strict` 给 `ad-review`/刷新用：降级 info 提级 warn 进候选重出。测试：`cd skills/ad-image/scripts && python3 -m pytest test_product_qc.py`。

## 生图后端治理（与 mv/n2d 同构，本线自持）

`生图AI` 默认 Codex；放行官方多参考一致性后端（OpenAI/gpt-image、Seedream Universal Reference、可灵主体库、Nano Banana、Sora Cameo）。两条硬闸门：① **项目内不混用后端** ② **禁第三方逆向/未授权出图**（即梦/Dreamina 逆向路径 forbidden）。判定逻辑见 `ad-craft/scripts/contract.py` `classify_image_backend`。

## 工作流

1. **建三层定妆库**（`出图/共享/`）：
   - 角色：每个出正/侧/背三视图 → `定妆_<角色>_三视图.png`。
   - 场景：关键场景四视图。
   3. **产品**：包装正/侧/背 + 关键细节（logo 特写、材质）→ `定妆_<产品>.png`。
      - **品牌色锁 (Hex-Lock)**：显式声明品牌 HEX 值，并在 Prompt 末尾追加 `color consistency: strict HEX #[value]`。
      - **Logo 保护区**：标记 Logo 坐标，禁止 AI 在 Logo 区域生成环境干扰（如遮挡、强反光）。
   2. **写视觉契约总览**（`出图/分镜/prompt/00_总览.md`）：继承 `storyboard.json.visual_contract`（品牌色/光位锚/画风/构图），逐镜带视线方向/光位/起幅余量。
   3. **万能安全区对账**：出图时，确保核心资产位于 8x8 网格中心，为多画幅裁切预留边缘。

4. 回写 `_进度.md` 出图 ✅：`python3 skills/ad-craft/scripts/progress_set.py set-stage "<作品根>" image --status ✅ --artifact 出图/分镜`，提示 `ad-video`。

## 广告专有强化

- **产品定妆 = 最严一致性**：包装文字/logo/品牌色/比例不能漂。绝不文生图产品（必 image2image + 产品参考图）。品牌色锁 HEX，logo 锁位置与最小留白。
- **品牌色锁**：`visual_contract.品牌色` 是硬约束，逐镜 prompt 带品牌主色，避免环境光把品牌色染偏。
- **KV 对齐**：`ad-concept` 的 KV 方向是主视觉锚，定妆库与关键镜要对住 KV。
- **多比例不重复出图**：按 `交付比例` 主比例出图，其它比例 `ad-compose` reframe（留够安全框余量，构图别贴边）。

## 一致性梯子（出图）
①参考图派生（默认）→ ②后端原生主体ID/主体库（Seedream/可灵/Sora Cameo·opt-in）→ ③LoRA（仅核心长线代言人）。锚点句（锁特征词）+ 身份锁定句（锁"同一张脸/同一个包装"）叠加用。产品/logo 用后端原生主体库或多参考最稳。

## 重抽预算策略（两档全局统一 · n2d/mv/ad 同义）

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
