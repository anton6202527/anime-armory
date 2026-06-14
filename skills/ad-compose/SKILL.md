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

> **自动 vs 操作者手工**：主片合成（含字幕烧录、混音、响度归一）+ cutdown + reframe 都已**真正出 MP4**（脚本调 ffmpeg），不再只是打印计划/滤镜串。先生成 `合成/_work/endcard.png`（`endcard.py`），下面各步即可一气产物落盘。**A/B 版本仍需操作者手工**（脚本只给 expected_path，不自动生成）。

1. **主片合成**（自动出片）：`bash skills/ad-compose/compose.sh "<作品根>" <主比例> [字幕语言 zh|en|bilingual|none] [交付规格]`
   - 拼 `出视频/分镜/视频/` clips：**始终 filter-concat 归一**（scale/pad/fps/setsar，按主比例），不用 `-c copy`（异构 clip 会静默产出损坏）；ffmpeg stderr 不再被吞。
   - 追加 **品牌包装 end card**（按主比例归一后接 2.5s）。
   - **字幕烧录**（步 2 已内联进 compose.sh）：`字幕语言≠none` 时自动调 `render_subs.py` 出字幕 PNG + overlay 链（`vfilter.txt`），再 overlay 烧进底片。
   - 混 VO（主）+ 音乐床（duck 到 ~25%）；占位 VO 会提醒不可定稿。
   - **交付规格响度归一**：成片有音轨时按 `交付规格`（平台默认 -16 LUFS / 广电TVC -23 LUFS）自动跑 ffmpeg `loudnorm` → `合成/成片_主片_loud.mp4`。
2. **字幕**：默认由 compose.sh 第 4 参数驱动；也可单独跑 `render_subs.py 脚本/字幕_zh.srt --out-dir 合成/_work/subs`（出 PNG + `vfilter.txt` 供 overlay）。
3. **多时长 cutdown**（自动出片）：`python3 cutdown.py "<作品根>" --target 15s --aspect <比例> --render` → 按镜头优先级保钩子/产品/CTA 重剪出 plan，并**实际**按 plan 取 clip filter-concat + 接 end card → `合成/cutdown/成片_15s.mp4`。镜头时长读权威 `脚本/镜头时长.json`；任一保留镜时长缺失 → block，拒绝出计划。无 ffmpeg 时只出 plan。
4. **多比例 reframe**（自动出片）：`python3 reframe.py --src 1920x1080 --target 9:16 --in 合成/成片_主片.mp4 --render [--crop-x 0.4 --crop-y 0.45]` → 实际跑 crop/pad 滤镜出 `合成/多比例/成片_9x16.mp4`。不传焦点=中心裁切（偏置主体会被裁掉，脚本会提示）；传 `--crop-x/--crop-y` 把裁切窗对到主体焦点。
5. **A/B 版本**：deliver.py 只给 expected_path，由操作者手工剪/导出。
6. **交付矩阵闭环**：跑 `python3 skills/ad-compose/deliver.py "<作品根>" --mark-existing` 生成 `合成/delivery_plan.json`（含每个交付件的可执行 `--render` 命令），并把已存在交付件回写 `_进度.md`。
7. 回写 `_进度.md` 剪辑包装 ✅：`python3 skills/ad-craft/scripts/progress_set.py set-stage "<作品根>" compose --status ✅ --artifact 合成`，提示 AI 披露（`ad-craft/ai_usage.py`）和 `ad-review`。

## 广告专有强化（差异化）

- **品牌包装 end card**：`endcard.py` 用品牌色背景 + logo + slogan + CTA 胶囊按钮（Pillow，无 libass 也能做）。关键 logo/包装文字用真素材，不靠 AI 生。
- **多时长 cutdown**：`cutdown.py` 不机械截断，按镜头优先级（CTA/产品/钩子必保）重剪——**必保镜先占预算、可选镜补剩余预算**（避免低优先级镜先吃预算把骨架挤溢出）；时长读权威 `镜头时长.json`，缺则 block（不会把 0s 骨架误判成通过）；`--render` 实际出 MP4，带 pytest。
- **多比例 reframe**：`reframe.py` 算裁切/加边滤镜并 `--render` 出片。默认中心裁切；`--crop-x/--crop-y` 指定归一焦点把裁切窗对到主体（偏置主体不被裁）。不传焦点时不再宣称 safe-area 感知，只提示主体居中假设。带 pytest。
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
