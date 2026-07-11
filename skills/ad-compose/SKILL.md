---
name: ad-compose
description: 拍广告 第7阶段·剪辑包装 + 多版本交付 — 拼 clips + 混 VO/音乐床/SFX（张力 ducking）+ 字幕（Pillow PNG overlay，无 libass）+ 品牌包装片尾 end card（logo+slogan+CTA）→ 成片_主片.mp4；再派生多时长 cutdown（30→15→6s，按镜头优先级重剪保钩子/产品/CTA）+ 多比例 reframe（16:9/9:16/1:1 中心裁切/加边）+ 交付规格归一（响度 LUFS·安全框）。Use when asked 广告合成/剪辑包装/成片/cutdown/多比例/多时长/片尾包装/交付/响度 for a 拍广告 project. Triggers 广告合成, 剪辑包装, 成片, 片尾包装, end card, cutdown, 多比例, 多时长, reframe, 交付, 响度, LUFS, 安全框, ad-compose.
---

# ad-compose — 拍广告 · 剪辑包装 + 多版本交付

把 clips 拼成成片并做**品牌包装 + 多版本交付**。

ffmpeg 无 libass 时，字幕走 Pillow PNG overlay。

## 偏好（私有）

按 `../skills/ad-craft/references/选择点与偏好.md` 读 `<作品根>/_设置.md`。涉及：`品牌包装模板`、`字幕语言`、`音乐来源`、`cutdown版本`、`交付比例`、`交付规格`。合成是**花钱/不可逆**阶段，正式跑前确认；开跑前先跑 `python3 skills/ad-craft/scripts/gate.py "<作品根>" --stage compose`。

> compose 不替平台烙统一 AI 水印；但合成后必须进入 `ad-craft` 发布合规 manifest，再由 `ad-review` 验收平台声明/标识责任和证据，不能把“平台外操作”当作无须留痕。

## 工作流

> **自动 vs 操作者手工**：主片合成（含字幕烧录、混音、响度归一）+ cutdown + reframe 都已**真正出 MP4**（脚本调 ffmpeg），不再只是打印计划/滤镜串。先生成 `合成/_work/endcard.png`（`endcard.py`），下面各步即可一气产物落盘。**A/B 版本仍需操作者手工**（脚本只给 expected_path，不自动生成）。

1. **主片合成**（自动出片）：`bash skills/ad-compose/compose.sh "<作品根>" <主比例> [字幕语言 zh|en|bilingual|none] [交付规格]`
   - 拼 `出视频/分镜/视频/` clips：**始终 filter-concat 归一**（scale/pad/fps/setsar，按主比例），不用 `-c copy`（异构 clip 会静默产出损坏）；ffmpeg stderr 不再被吞。
   - 运行 `compose_preflight.py`：storyboard 已含 end card 时不重复追加；只有确实缺片尾才补品牌包装。
   - **字幕烧录**（步 2 已内联进 compose.sh）：`字幕语言≠none` 时自动调 `render_subs.py` 出字幕 PNG + overlay 链（`vfilter.txt`），再 overlay 烧进底片。
   - 混 VO（主）+ 音乐床（duck 到 ~25%）；占位 VO 会提醒不可定稿。
   - **交付规格响度归一**：目标统一读 ad-craft contract；临时文件原位替换正式 `成片_主片.mp4`，避免“进度指向未归一版本”。
2. **字幕**：默认由 compose.sh 第 4 参数驱动；也可单独跑 `render_subs.py 脚本/字幕_zh.srt --out-dir 合成/_work/subs`（出 PNG + `vfilter.txt` 供 overlay）。
3. **多时长 cutdown**：按镜头优先级选段，但渲染从已混音/字幕/包装的主片精确 trim，保留 VO、音乐、字幕；不再从无声 clips 重拼，也不重复加 end card。
4. **多比例 reframe**：支持固定 `--crop-x/--crop-y`，也支持 `--focus-plan` 按时间段动态跟随主体；高价值竖版不得默认中心裁切后直接交付。
5. **A/B 版本**：deliver.py 只给 expected_path，由操作者手工剪/导出。
6. **逐交付件实测 QC**：`deliver.py` 生成 `delivery_qc.json`，用 ffprobe/ffmpeg 实测时长、视频/音轨、分辨率/比例、integrated LUFS 与 true peak；只把通过项回写 ✅。
7. 回写 compose 后先跑 `ai_usage.py` + `compliance_manifest.py`，再进入 `ad-review`。

## 广告专有强化（差异化）

- **品牌包装 end card**：`endcard.py` 用品牌色背景 + logo + slogan + CTA 胶囊按钮（Pillow，无 libass 也能做）。关键 logo/包装文字用真素材，不靠 AI 生。
- **多时长 cutdown**：`cutdown.py` 不机械截断，按镜头优先级（CTA/产品/钩子必保）重剪——**必保镜先占预算、可选镜补剩余预算**（避免低优先级镜先吃预算把骨架挤溢出）；时长读权威 `镜头时长.json`，缺则 block（不会把 0s 骨架误判成通过）；`--render` 实际出 MP4，带 pytest。
- **多比例 reframe**：`reframe.py` 算裁切/加边滤镜并 `--render` 出片。默认中心裁切；`--crop-x/--crop-y` 指定归一焦点把裁切窗对到主体（偏置主体不被裁）。不传焦点时不再宣称 safe-area 感知，只提示主体居中假设。带 pytest。
- **交付规格**：响度归一（LUFS）+ 安全框 + 帧率，是广告投放硬指标。

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
