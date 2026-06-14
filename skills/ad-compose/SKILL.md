---
name: ad-compose
description: 拍广告 第7阶段·剪辑包装 + 多版本交付 — 拼 clips + 混 VO/音乐床/SFX（张力 ducking）+ 字幕（Pillow PNG overlay，无 libass）+ 品牌包装片尾 end card（logo+slogan+CTA）→ 成片_主片.mp4；再派生多时长 cutdown（30→15→6s，按镜头优先级重剪保钩子/产品/CTA）+ 多比例 reframe（16:9/9:16/1:1 中心裁切/加边）+ 交付规格归一（响度 LUFS·安全框）。ad-* 自包含，不复用 n2d-compose。Use when asked 广告合成/剪辑包装/成片/cutdown/多比例/多时长/片尾包装/交付/响度 for a 拍广告 project. Triggers 广告合成, 剪辑包装, 成片, 片尾包装, end card, cutdown, 多比例, 多时长, reframe, 交付, 响度, LUFS, 安全框, ad-compose.
---

# ad-compose — 拍广告 · 剪辑包装 + 多版本交付

把 clips 拼成成片并做**品牌包装 + 多版本交付**——这是广告线相对 n2d 的后端强化。

**自包含**：不复用 `n2d-compose`；ffmpeg 无 libass，字幕走 Pillow PNG overlay。

## 偏好（私有）

按 `../skills/ad-craft/references/选择点与偏好.md` 读 `<作品根>/_设置.md`。涉及：`品牌包装模板`、`字幕语言`、`音乐来源`、`cutdown版本`、`交付比例`、`交付规格`。合成是**花钱/不可逆**阶段，正式跑前确认；开跑前先跑 `python3 skills/ad-craft/scripts/gate.py "<作品根>" --stage compose`。

> **AI 标识/水印不再由本流水线处理**：ad-compose 出成片/交付件即收尾，不再生成可见 AI 标识/水印、不再调用任何 watermark skill。若投放地区/平台需要 AI 标识或披露，由使用方在工具之外按当地法规自行处理（`ad-craft/ai_usage.py` 仍记录 AI 使用披露文本）。

## 工作流

1. **主片合成**：`bash skills/ad-compose/compose.sh "<作品根>" <主比例>`
   - 拼 `出视频/分镜/视频/` clips（接缝按 storyboard `transition`，默认硬切裸拼）。
   - 混 VO（主）+ 音乐床（duck 到 ~25%）+ SFX；占位 VO 会提醒不可定稿。
   - 追加 **品牌包装 end card**（先 `endcard.py` 生成 `合成/_work/endcard.png`）。
2. **字幕烧录**（按 `字幕语言`）：`render_subs.py 脚本/字幕_zh.srt --out-dir 合成/_work/subs` → PNG overlay。
3. **多时长 cutdown**：`python3 cutdown.py "<作品根>" --target 15s` → 按镜头优先级保钩子/产品/CTA 重剪，出 plan，再按 plan 拼 `合成/cutdown/成片_15s.mp4`。
4. **多比例 reframe**：`python3 reframe.py --src 1920x1080 --target 9:16` → ffmpeg crop/pad 滤镜 → `合成/多比例/成片_9x16.mp4`。
5. **交付规格归一**：按 `交付规格`（平台默认 -16 LUFS / 广电 TVC -23 LUFS）用 ffmpeg `loudnorm` 归一响度、确认安全框。
6. **交付矩阵闭环**：跑 `python3 skills/ad-compose/deliver.py "<作品根>" --mark-existing` 生成 `合成/delivery_plan.json`，并把已存在交付件回写 `_进度.md`。
7. 回写 `_进度.md` 剪辑包装 ✅：`python3 skills/ad-craft/scripts/progress_set.py set-stage "<作品根>" compose --status ✅ --artifact 合成`，提示 AI 披露（`ad-craft/ai_usage.py`）和 `ad-review`。

## 广告专有强化（差异化）

- **品牌包装 end card**：`endcard.py` 用品牌色背景 + logo + slogan + CTA 胶囊按钮（Pillow，无 libass 也能做）。关键 logo/包装文字用真素材，不靠 AI 生。
- **多时长 cutdown**：`cutdown.py` 不机械截断，按镜头优先级（CTA/产品/钩子必保）重剪，凑目标时长 ±容差，带 pytest。
- **多比例 reframe**：`reframe.py` 算中心裁切/加边滤镜，主体留 action-safe 才不被竖版裁掉，带 pytest。
- **交付规格**：响度归一（LUFS）+ 安全框 + 帧率，是广告投放硬指标（n2d 没有）。

## 接缝处理（治"剪起来跳"）

读 `storyboard.json` 每接缝 `continuity.transition`：硬切裸拼 / 跳变未焊→局部 xfade 微溶解 / 缺空镜→报警不伪造。有意硬切（如反转）不溶解。

## 测试

```bash
cd skills/ad-compose && python3 test_cutdown_reframe.py
```

## 常见错误

| 错误 | 纠正 |
|---|---|
| 占位 VO 直接出成片 | 占位只做 demo；正式片用真 VO 复跑（音画才准）|
| cutdown 机械截前 15s | 按镜头优先级保钩子/产品/CTA 重剪，别砍掉记忆点 |
| 竖版直接拉伸变形 | 用 reframe crop/pad；主体冲出安全框就重构图 |
| 不归一响度 | 按 `交付规格` loudnorm 到目标 LUFS，否则平台拒收/忽大忽小 |
| 关键 logo/包装文字靠 AI 生 | end card / 包装文字用真素材合成 |
