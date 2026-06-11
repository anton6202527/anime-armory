---
name: ad-video
description: 拍广告 第6阶段·图生视频 — 把 ad-image 的首帧 PNG 按 storyboard.json 逐镜图生视频，写 Clip 视频 prompt（运镜+表演+节奏），按镜头类型做模型路由（产品展示镜/情绪镜/demo实拍质感/手持 → primary/fallback），机检出图→出视频视觉契约继承（品牌色/光位/轴线漂移=block），首尾双帧接力焊接。ad-* 自包含，不复用 n2d-video；用通用生视频 CLI（即梦/可灵/Veo/Seedance/manual）。Use when asked 广告出视频/图生视频/视频prompt/运镜/模型路由/契约继承 for a 拍广告 project. Triggers 广告出视频, 图生视频, 视频prompt, 运镜, 模型路由, 契约继承, image2video, ad-video.
---

# ad-video — 拍广告 · 图生视频

把 `ad-image` 的首帧 PNG 按 `storyboard.json` 逐镜**图生视频**：写 Clip 视频 prompt（运镜+表演+节奏），机检视觉契约继承，按镜头类型路由后端，首尾双帧接力。

**自包含**：不复用 `n2d-video`；用通用生视频 CLI（即梦/可灵/Veo/Seedance/manual）。

## 偏好（私有）

按 `../_偏好约定.md` 读 `<作品根>/_设置.md`。涉及：`生视频AI`、`视频模型路由`、`出视频规格`、`视频分辨率`、`交付比例`。出视频是**花钱/高风险**阶段，正式跑前确认规格。

## 工作流

1. **逐 Clip 视频 prompt**（`出视频/分镜/prompt/`）：在首帧基础上写运镜（推/拉/摇/环绕/手持）+ 表演节拍 + 节奏。继承 `storyboard.json.visual_contract`（品牌色/光位/轴线/景别）。
2. **模型路由**（`视频模型路由=自动按镜头路由` 时）：按镜头类型选 primary/fallback（见 `references/platforms.md`）：
   - 产品展示/环绕 hero → 稳定+主体一致后端（Seedance/可灵主体库）
   - 情绪/人物特写 → 电影感后端（Veo）
   - demo 实拍质感/手持 → 真实感后端
   - 普通镜/兜底 → `生视频AI`（默认即梦）
3. **契约继承机检（硬闸门）**：
   ```bash
   python3 skills/ad-video/scripts/inherit_contract.py "<作品根>" --json "<作品根>/出视频/分镜/contract_inheritance.json"
   ```
   品牌色/光位锚/轴线未继承 = 🔴 block（广告产品色一漂就废）。0 block 才生成。
4. **图生视频**：调生视频 CLI，标 `need_end_frame` 的用首+尾双帧引导焊接点。
5. 回写 `_进度.md` 视频 ✅，提示 `ad-compose`。

## 广告专有强化

- **品牌色继承是硬闸门**：`inherit_contract.py` 把品牌色/光位/轴线漂移拦在生成前（n2d 的契约继承基础上，广告加了品牌色这条像素级硬约束）。
- **产品镜稳定优先**：产品 hero 镜路由到主体一致性最强的后端，避免 image2video 把包装/logo 抖花。
- **运镜服务节奏**：广告节奏紧，一镜一个主运镜，动作峰值对 VO/音乐床节奏点（`ad-script` 时间轴标）。
- **多比例**：按主比例出视频，其它比例 `ad-compose` reframe；运镜别让主体/产品冲出 action-safe。

## 测试

```bash
cd skills/ad-video/scripts && python3 test_inherit_contract.py
```

## 常见错误

| 错误 | 纠正 |
|---|---|
| 视频 prompt 丢了品牌色/光位 | `inherit_contract.py` block；逐镜继承 visual_contract |
| 产品镜用普通后端抖花包装 | 产品 hero 路由主体一致后端 + 首尾双帧 |
| 项目内混用视频后端当默认 | 路由是按镜头选 primary/fallback，不是随意混；记录在路由表 |
| 运镜让产品/主体冲出安全框 | 留 action-safe 余量，多比例 reframe 才不裁掉主体 |
