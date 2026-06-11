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

按 `../_偏好约定.md` 读 `<作品根>/_设置.md`。涉及：`生图AI`、`一致性增强`、`基础视觉风格`、`交付比例`（出图按主比例，cutdown 比例由 `ad-compose` reframe，不重复出图）、`生成粒度`。出图是**花钱/高风险**阶段，正式跑前确认。

## 生图后端治理（与 mv/n2d 同构，本线自持）

`生图AI` 默认 Codex；放行官方多参考一致性后端（OpenAI/gpt-image、Seedream Universal Reference、可灵主体库、Nano Banana、Sora Cameo）。两条硬闸门：① **项目内不混用后端** ② **禁第三方逆向/未授权出图**（即梦/Dreamina 逆向路径 forbidden）。判定逻辑见 `ad-craft/scripts/contract.py` `classify_image_backend`。

## 工作流

1. **建三层定妆库**（`出图/共享/`）：
   - 角色：每个出正/侧/背三视图 → `定妆_<角色>_三视图.png`。
   - 场景：关键场景四视图。
   - **产品**：包装正/侧/背 + 关键细节（logo 特写、材质）→ `定妆_<产品>.png`，写死品牌色 HEX、logo 位置、禁改清单（见 `references/产品一致性checklist.md`）。
2. **写视觉契约总览**（`出图/分镜/prompt/00_总览.md`）：继承 `storyboard.json.visual_contract`（品牌色/光位锚/画风/构图），逐镜带视线方向/光位/起幅余量。
3. **逐镜出图**：按 `storyboard.json` 每镜 prompt 出首帧；产品镜必引用产品定妆 `PROD_xx` 参考组 + 身份锁定句；标 `need_end_frame` 的出尾帧。
4. 回写 `_进度.md` 出图 ✅，提示 `ad-video`。

## 广告专有强化

- **产品定妆 = 最严一致性**：包装文字/logo/品牌色/比例不能漂。绝不文生图产品（必 image2image + 产品参考图）。品牌色锁 HEX，logo 锁位置与最小留白。
- **品牌色锁**：`visual_contract.品牌色` 是硬约束，逐镜 prompt 带品牌主色，避免环境光把品牌色染偏。
- **KV 对齐**：`ad-concept` 的 KV 方向是主视觉锚，定妆库与关键镜要对住 KV。
- **多比例不重复出图**：按 `交付比例` 主比例出图，其它比例 `ad-compose` reframe（留够安全框余量，构图别贴边）。

## 一致性梯子（出图）
①参考图派生（默认）→ ②后端原生主体ID/主体库（Seedream/可灵/Sora Cameo·opt-in）→ ③LoRA（仅核心长线代言人）。锚点句（锁特征词）+ 身份锁定句（锁"同一张脸/同一个包装"）叠加用。产品/logo 用后端原生主体库或多参考最稳。

## 常见错误

| 错误 | 纠正 |
|---|---|
| 文生图产品（包装/logo 全靠描述） | 必 image2image + 产品定妆参考；文生图必漂 |
| 品牌色被环境光染偏 | 锁 `visual_contract.品牌色` HEX，逐镜 prompt 带品牌主色 |
| 每个交付比例都重新出图 | 按主比例出图，其它比例 ad-compose reframe，构图留安全框 |
| 项目内混用生图后端 | 一个项目锁一个后端；切换要记录并重出受影响图 |
| logo 摆错位/被裁 | 产品 checklist 锁 logo 位置与最小留白 |
