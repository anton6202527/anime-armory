---
name: ad-video
description: 拍广告 第6阶段·图生视频 — 把 ad-image 的首帧 PNG 按 storyboard.json 逐镜图生视频，写 Clip 视频 prompt（运镜+表演+节奏），按镜头类型做模型路由（产品展示镜/情绪镜/demo实拍质感/手持 → primary/fallback），机检出图→出视频视觉契约继承（品牌色/光位/轴线漂移=block），首尾双帧接力焊接。ad-* 自包含，不复用 n2d-video；用通用生视频模型/渠道（Seedance/Veo/Kling/即梦/可灵/manual 等）。Use when asked 广告出视频/图生视频/视频prompt/运镜/模型路由/契约继承 for a 拍广告 project. Triggers 广告出视频, 图生视频, 视频prompt, 运镜, 模型路由, 契约继承, image2video, ad-video.
---

# ad-video — 拍广告 · 图生视频

把 `ad-image` 的首帧 PNG 按 `storyboard.json` 逐镜**图生视频**：写 Clip 视频 prompt（运镜+表演+节奏），机检视觉契约继承，按镜头类型路由后端，首尾双帧接力。

**自包含**：不复用 `n2d-video`；用通用生视频模型/渠道（Seedance/Veo/Kling/即梦/可灵/manual 等）。

## 偏好（私有）

按 `../skills/ad-craft/references/选择点与偏好.md` 读 `<作品根>/_设置.md`。涉及：`生视频模型`、`生视频渠道`、`视频模型路由`、`出视频规格`、`视频分辨率`、`交付比例`。出视频是**花钱/高风险**阶段，正式跑前确认规格；写完视频 prompt 并跑完契约继承机检后、正式生成前跑 `python3 skills/ad-craft/scripts/gate.py "<作品根>" --stage video`。

## 上游契约单一真值源

品牌色 HEX / 光位锚 / 轴线在**出图阶段**烤进首帧像素，所以契约继承的上游真值源是：

1. **首选** `出图/分镜/prompt/00_总览.md` 的「视觉一致性契约」节（出图细化后的最终值）；
2. **回退** `脚本/storyboard.json`.visual_contract（出图总览尚未生成时的脚本种子）。

`inherit_contract.py` 与 `references/platforms.md` 都以此口径为准（与 n2d 的 image→video diff 同源）。

## 工作流

1. **模型路由**（先于写 prompt）：
   ```bash
   python3 skills/ad-video/scripts/route.py "<作品根>"   # 写 出视频/分镜/prompt/video_model_routes.json
   ```
   按镜型**能力**（不是后端品牌字串）路由 primary/fallback + 单 Clip 时长上限校验（见 `references/platforms.md`）：
   - 产品展示/环绕 hero、绑定 `PROD_*` → 主体一致性强（Seedance/可灵主体库）
   - 情绪/人物特写 → 电影感后端（Veo/可灵）
   - demo 实拍质感/手持 → 真实运动后端
   - 空镜/痛点/普通镜 → 通用后端（`_设置.md` 的 `生视频模型`/`生视频渠道`，旧 `生视频AI` 兼容）
   - end card/包装定格 → 静帧或极慢运镜
   - 镜头时长超 primary 后端单 Clip 上限 = 🔴 block（改用更长后端或拆镜）。
2. **逐 Clip 视频 prompt**（`出视频/分镜/prompt/镜头N.md`）：在首帧基础上写运镜（推/拉/摇/环绕/手持）+ 表演节拍 + 节奏。逐镜继承上游契约（品牌色/光位/轴线/景别）；**绑定 `PROD_*` 的产品镜必须重写产品身份锁定句/资产引用（`PROD_xx` 或「同一包装/同一 logo/同一品牌色」）**。
3. **契约继承机检（硬闸门）**：
   ```bash
   python3 skills/ad-video/scripts/inherit_contract.py "<作品根>" --json "<作品根>/出视频/分镜/contract_inheritance.json"
   ```
   品牌色/光位锚/轴线未继承、产品镜丢产品身份锁定 = 🔴 block（广告产品色/形态一漂就废）。0 block 才生成。
4. **图生视频**：调生视频 CLI，标 `need_end_frame` 的用首+尾双帧引导焊接点。
5. 回写 `_进度.md` 视频 ✅：`python3 skills/ad-craft/scripts/progress_set.py set-stage "<作品根>" video --status ✅ --artifact 出视频/分镜/视频`，提示 `ad-compose`。

## 广告专有强化

- **品牌色 + 产品形态继承是硬闸门**：`inherit_contract.py` 把品牌色/光位/轴线漂移、产品镜丢产品身份锁定句拦在生成前（n2d 的契约继承基础上，广告加了品牌色 + 产品形态这两条像素级硬约束）。
- **产品镜稳定优先**：产品 hero 镜路由到主体一致性最强的后端，避免 image2video 把包装/logo 抖花。
- **运镜服务节奏**：广告节奏紧，一镜一个主运镜，动作峰值对 VO/音乐床节奏点（`ad-script` 时间轴标）。
- **多比例**：按主比例出视频，其它比例 `ad-compose` reframe；运镜别让主体/产品冲出 action-safe。

## 测试

```bash
cd skills/ad-video/scripts && python3 -m pytest
```

## 常见错误

| 错误 | 纠正 |
|---|---|
| 视频 prompt 丢了品牌色/光位 | `inherit_contract.py` block；逐镜继承上游契约（出图 00_总览 → storyboard 回退） |
| 品牌色 HEX 与 rgb()/别名写法不同被误判漂移 | `inherit_contract.py` 归一化 HEX 比对，同色不同写法不 block |
| 产品镜 prompt 丢了产品身份锁定句 | `inherit_contract.py` 产品形态 block；重写 `PROD_xx`/「同一包装/同一 logo/同一品牌色」 |
| 产品镜用普通后端抖花包装 | `route.py` 按能力把产品镜路由主体一致后端 + 首尾双帧 |
| 镜头比后端单 Clip 上限还长 | `route.py` 时长上限 block；换更长后端（Seedance≤15s）或拆镜 |
| 项目内混用视频后端当默认 | 路由按能力选 primary/fallback 落 `video_model_routes.json`，不是随意混 |
| 运镜让产品/主体冲出安全框 | 留 action-safe 余量，多比例 reframe 才不裁掉主体 |
