---
name: ad-compose
description: 拍广告 第7阶段·剪辑包装 + 多版本交付 — 拼 clips + 混 VO/音乐床/SFX + 字幕 + 品牌包装 → 主片；派生 claim/披露原子化 cutdown 与多比例 reframe；逐件实测技术规格、最终像素文字、ASR 四路文案、无障碍与实际 AI provenance。Use when asked 广告合成/剪辑包装/成片/cutdown/多比例/多时长/片尾包装/交付/响度/色彩/字幕/OCR/ASR/无障碍/C2PA for a 拍广告 project. Triggers 广告合成, 剪辑包装, 成片, 片尾包装, end card, cutdown, 多比例, 多时长, reframe, 交付, 响度, LUFS, 安全框, BT.709, 字幕, OCR, ASR, C2PA, 闪烁, ad-compose.
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
   - 先写 `合成/color_preflight.json`：HDR/BT.2020/混合色彩源没有显式转换方案即 block；不能仅改标签冒充 BT.709。
   - 运行 `compose_preflight.py`：storyboard 已含 end card 时不重复追加；只有确实缺片尾才补品牌包装。
   - **字幕烧录**（步 2 已内联进 compose.sh）：`字幕语言≠none` 时自动调 `render_subs.py` 出字幕 PNG + overlay 链（`vfilter.txt`），再 overlay 烧进底片。
   - 混 VO（主）+ 音乐床（duck 到 ~25%）；占位 VO 会提醒不可定稿。
   - **交付规格响度归一**：目标统一读 ad-craft contract；临时文件原位替换正式 `成片_主片.mp4`，避免“进度指向未归一版本”。
2. **字幕**：默认由 compose.sh 第 4 参数驱动；也可单独跑 `render_subs.py 脚本/字幕_zh.srt --out-dir 合成/_work/subs`（出 PNG + `vfilter.txt` 供 overlay）。
3. **多时长 cutdown**：按镜头优先级选段，但渲染从已混音/字幕/包装的主片精确 trim；选中 `claim_ids` 时自动补回对应 disclosure 镜，缺披露直接 block。
4. **多比例 reframe**：覆盖 16:9/9:16/4:5/1:1，支持固定 `--crop-x/--crop-y` 或 `--focus-plan` 动态跟随；高价值版位不得默认中心裁切后直接交付。
5. **A/B 版本**：deliver.py 只给 expected_path，由操作者手工剪/导出。
6. **逐交付件技术 QC**：`deliver.py` 先写本次 `delivery_plan.json`，再生成 `delivery_qc.json`；实测时长、实际 placement 比例/分辨率/音轨、编解码、48 kHz、帧率、LUFS/true peak、BT.709/range/progressive。
7. **最终像素文字 QC**：先用 `rendered_text_qc.py --init-plan` 登记每版字幕、CTA、价格、claim 和法律声明的时间窗/框；在最终编码文件抽帧，OCR/像素对比度只定位，具名人逐项确认精确文案、对比度、停留时间和遮挡并留证。
8. **ASR 四路对账**：`asr_consistency.py` 对 `voiceover.txt → 实际 VO transcript → 字幕 → 最终母版 transcript`；数字、价格、CTA、spoken claim 和法律声明精确匹配。可用 `deliver.py --run-asr` 调本地 whisper；预计算 transcript 也须在 `asr_receipts.json` 绑定媒体/文本 SHA、引擎/模型与时间，缺证据即 block。
9. **无障碍 QC**：`accessibility_qc.json` 验完整字幕、逐事件非语言音频字幕，并按项目 WCAG 2.2 目标要求音频描述或媒体替代；阅读速度/自动对比度/低分辨率闪烁仅作快筛。
10. **最终文件 provenance**：`provenance_qc.py` 对每个实际交付件跑 c2patool/ffprobe；本地工具或容器不承载时，只接受绑定当前媒体 SHA 的外部探测回执。`metadata_status=preserve` 文字不能通过。
11. `--mark-existing` 只有在上述最终媒体 QC 全部 0 block 时才回写交付件 ✅；随后跑 locale/release variant/compliance，再进入 `ad-review`。

## 广告专有强化（差异化）

- **品牌包装 end card**：`endcard.py` 用品牌色背景 + logo + slogan + CTA 胶囊按钮（Pillow，无 libass 也能做）。关键 logo/包装文字用真素材，不靠 AI 生。
- **多时长 cutdown**：`cutdown.py` 不机械截断，按 CTA/产品/钩子重剪，并把 claim+披露作为原子组合；时长读权威 `镜头时长.json`，缺则 block。
- **多比例 reframe**：`reframe.py` 算裁切/加边滤镜并 `--render` 出片。默认中心裁切；`--crop-x/--crop-y` 指定归一焦点把裁切窗对到主体（偏置主体不被裁）。不传焦点时不再宣称 safe-area 感知，只提示主体居中假设。带 pytest。
- **交付规格按权威分层**：`平台默认 -16 LUFS/-1 dBTP` 是内部数字母版，不冒充平台统一官方值；`广电TVC -23 LUFS/-1 dBTP` 对应 EBU R128 programme recommendation；客户/播出机构书面规格优先并在项目留证。安全区必须按实际 placement 模板，不能从响度 profile 推断。
- **SDR 色彩母版**：BT.709 是本线内部 SDR 交付档；HDR 项目必须有转换/监看/批准证据。`compose_preflight` 查源，`delivery_qc` 查最终文件，二者不能互相替代。

## 接缝处理（治"剪起来跳"）

读 `storyboard.json` 每接缝 `continuity.transition`：硬切裸拼 / 跳变未焊→局部 xfade 微溶解 / 缺空镜→报警不伪造。有意硬切（如反转）不溶解。

## 测试

```bash
cd skills/ad-compose && python3 -m pytest test_cutdown_reframe.py test_accessibility_qc.py test_compose_preflight.py test_rendered_text_qc.py test_provenance_qc.py test_deliver_orchestration.py
```

## 常见错误

| 错误 | 纠正 |
|---|---|
| 占位 VO 直接出成片 | 占位只做 demo；正式片用真 VO 复跑（音画才准）|
| cutdown 机械截前 15s | 按镜头优先级保钩子/产品/CTA 重剪，别砍掉记忆点 |
| cutdown 留数据大字却删来源/免责 | 用同一 `claim_id` 绑定 disclosure；脚本会自动补回或 block |
| 竖版直接拉伸变形 | 用 reframe crop/pad；主体冲出安全框就重构图 |
| HDR/BT.2020 直接打 BT.709 标签 | 先做显式色彩转换与监看留证；仅改 metadata 会造成色偏/高光错误 |
| 有 VO 却无字幕，或机器说“无闪烁”就放行 | 缺字幕会 block；闪烁扫描只作 WARN，最终仍需具名复核 |
| OCR 找到了文字就当通过 | OCR/视觉模型只定位；逐条记录 observed_text、具名审片、对比度/时长/遮挡确认和证据 |
| `metadata_status=preserve` 就当 C2PA/隐式标识存在 | 必须探测最终文件，或提供绑定当前 SHA 的 c2patool/供应商/平台探测回执 |
| 把 -16 LUFS 写成所有平台官方要求 | 它是内部数字母版；客户/平台书面规格优先，广电参考 EBU R128 -23 LUFS/-1 dBTP |
| 关键 logo/包装文字靠 AI 生 | end card / 包装文字用真素材合成 |
