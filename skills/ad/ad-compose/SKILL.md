---
name: ad-compose
description: 拍广告 第7阶段·剪辑包装 + 多版本交付 — 拼 clips + 混 VO/音乐床/SFX + 字幕 + 品牌包装 → 主片；派生 claim/披露原子化 cutdown，并按逐 placement 计划做原生 recrop/re-edit/variant 或经签核的机械 reframe；统一 render profile，逐件实测技术规格、最终像素文字、ASR、无障碍与实际 AI provenance。Use when asked 广告合成/剪辑包装/成片/cutdown/多比例/多时长/片尾包装/交付/响度/色彩/字幕/OCR/ASR/无障碍/C2PA for a 拍广告 project. Triggers 广告合成, 剪辑包装, 成片, 片尾包装, end card, cutdown, 多比例, 多时长, reframe, 交付, 响度, LUFS, 安全框, BT.709, 字幕, OCR, ASR, C2PA, 闪烁, ad-compose.
---

# ad-compose — 拍广告 · 剪辑包装 + 多版本交付

把 clips 拼成成片并做**品牌包装 + 多版本交付**。

ffmpeg 无 libass 时，字幕走 Pillow PNG overlay。

## 偏好（私有）

按 `../skills/ad/ad-craft/references/选择点与偏好.md` 读 `<作品根>/_设置.md`。涉及：`品牌包装模板`、`字幕语言`、`音乐来源`、`cutdown版本`、`交付比例`、`交付规格`。合成是**花钱/不可逆**阶段，正式跑前确认；开跑前先跑 `python3 skills/ad/ad-craft/scripts/gate.py "<作品根>" --stage compose`。

> compose 不替平台烙统一 AI 水印；但合成后必须进入 `ad-craft` 发布合规 manifest，再由 `ad-review` 验收平台声明/标识责任和证据，不能把“平台外操作”当作无须留痕。

## 工作流

> **自动 vs 原生适配**：主片合成与同画幅 cutdown 自动出 MP4。跨比例行不再天然等于中心裁切许可：`deliver.py` 先生成 `生产数据/placement_adaptation.json`。`native_recrop/native_reedit/native_variant` 输出结构化原生制作指令；reedit/variant 的 shot plan 逐镜绑定真实 `source_path(s)`，收据必须消费全部当前源素材。只有 `mechanical_reframe` 已绑定具名批准、placement 安全区、逐镜 focus plan 与当前证据时才生成可执行 ffmpeg 命令。跨比例成片还必须生成 `生产数据/placement_adaptation_receipts/<deliverable_id>.json`，绑定实际模式、输入/输出 SHA、profile SHA 与 adaptation digest；批准 native 模式却交机械裁切文件会 block。A/B 版本仍由操作者按计划制作。

1. **主片合成**（自动出片）：`bash skills/ad/ad-compose/compose.sh "<作品根>" <主比例> [字幕语言 zh|en|bilingual|none] [交付规格]`
   - 先由 `render_profile.py` 编译唯一 `生产数据/render_profile.json`，分开记录后端原生 source resolution 与母版容器 resolution/FPS/upscale policy；route、runner、delivery plan/QC 绑定同一 profile SHA，compose/cutdown 读取同一 profile。720p 源装进 1080p 容器只记 upscale，不得宣称原生 1080p。
   - 拼 `出视频/分镜/视频/` clips：**始终 filter-concat 归一**（scale/pad/fps/setsar，按 profile 主比例），不用 `-c copy`（异构 clip 会静默产出损坏）；ffmpeg stderr 不再被吞。
   - 先写 `合成/color_preflight.json`：HDR/BT.2020/混合色彩源没有显式转换方案即 block；不能仅改标签冒充 BT.709。
   - 运行 `compose_preflight.py`：storyboard 已含 end card 时不重复追加；只有确实缺片尾才补品牌包装。
   - **字幕烧录**（步 2 已内联进 compose.sh）：`字幕语言≠none` 时自动调 `render_subs.py` 出字幕 PNG + overlay 链（`vfilter.txt`），再 overlay 烧进底片。
   - 混 VO（主）+ 音乐床（duck 到 ~25%）；占位 VO 会提醒不可定稿。
   - **交付规格响度归一**：目标统一读 ad-craft contract；临时文件原位替换正式 `成片_主片.mp4`，避免“进度指向未归一版本”。
2. **字幕**：默认由 compose.sh 第 4 参数驱动；也可单独跑 `render_subs.py 脚本/字幕_zh.srt --out-dir 合成/_work/subs`（出 PNG + `vfilter.txt` 供 overlay）。
3. **多时长 cutdown**：按镜头优先级选段，但渲染从已混音/字幕/包装的主片精确 trim；选中 `claim_ids` 时自动补回对应 disclosure 镜，缺披露直接 block。
4. **多比例 placement adaptation**：覆盖 16:9/9:16/4:5/1:1，但逐交付件选择原生 recrop/re-edit/variant。原生 re-edit/variant 的 shot plan 每镜写源素材路径，执行收据逐一对账；结构性文字、CTA、法律声明或产品安全区风险优先 `native_reedit`。机械 reframe 只消费已批准的逐镜 `--focus-plan`，不存在“无焦点也自动过”的路径。
5. **A/B 版本**：deliver.py 只给 expected_path，由操作者手工剪/导出。
6. **逐交付件技术 QC**：`deliver.py` 先写本次 `delivery_plan.json`，再生成 `delivery_qc.json`；QC 绑定 plan、profile、adaptation、逐件媒体内容 SHA 与 execution receipt，并实测时长、实际 placement 比例/分辨率/音轨、编解码、48 kHz、帧率、LUFS/true peak、BT.709/range/progressive。另按行规查 **textless 无字版母版**：成片带烧录文字或 locale matrix 多语言时，交付计划须含 id/label 带 `textless`/`无字` 的母版件（缺=warn `textless_master_missing`）——否则每个语言版/改字都要回炉重做 online。烧录法律行/脚注停留时长按字数换算快筛（>12 字/秒 warn `rendered_text_reading_speed_warn`，见 rendered_text_qc）。
7. **最终像素文字 QC**：先用 `rendered_text_qc.py --init-plan` 登记每版字幕、CTA、价格、claim 和法律声明的时间窗/框；在最终编码文件抽帧，OCR/像素对比度只定位，具名人逐项确认精确文案、对比度、停留时间和遮挡并留证。
8. **ASR 四路对账**：`asr_consistency.py` 对 `voiceover.txt → 实际 VO transcript → 字幕 → 最终母版 transcript`；数字、价格、CTA、spoken claim 和法律声明精确匹配。可用 `deliver.py --run-asr` 调本地 whisper；预计算 transcript 也须在 `asr_receipts.json` 绑定媒体/文本 SHA、引擎/模型与时间，缺证据即 block。
9. **无障碍 QC**：`accessibility_qc.json` 验完整字幕、逐事件非语言音频字幕，并按项目 WCAG 2.2 目标要求音频描述或媒体替代；阅读速度/自动对比度/低分辨率闪烁仅作快筛。
10. **最终文件 provenance**：`provenance_qc.py` 对每个实际交付件跑 c2patool/ffprobe；本地工具或容器不承载时，只接受绑定当前媒体 SHA 的外部探测回执。`metadata_status=preserve` 文字不能通过。
11. **发布与投放就绪**：release variant 对每个 placement 分开校验 AI-origin label receipt 与 commercial/paid-partnership disclosure receipt；二者不可互代。`campaign_readiness.py` 另查落地页与跳转、offer/claim/CTA/价格对账、行业准入、conversion tracking/diagnostics、归因、UTM/deep link、consent/privacy。正式模式缺证据即 block；样片永不标 release-ready。
12. `--mark-existing` 只有上述最终媒体 QC 全部 0 block 时才回写交付件 ✅；随后跑 locale/release variant/campaign readiness/compliance，再进入 `ad-review`。

## 广告专有强化（差异化）

- **品牌包装 end card**：`endcard.py` 用品牌色背景 + logo + slogan + CTA 胶囊按钮（Pillow，无 libass 也能做）。关键 logo/包装文字用真素材，不靠 AI 生。
- **多时长 cutdown**：`cutdown.py` 不机械截断，按 CTA/产品/钩子重剪，并把 claim+披露作为原子组合；时长读权威 `镜头时长.json`，缺则 block。
- **多比例适配**：`placement_adaptation.py` 是模式与证据真值；`reframe.py` 只是获准机械路径的执行器。它能按逐镜 focus plan 动态裁切，但不能自行判断创意结构、安全区或文字重排；仅调用底层脚本而没有当前 execution receipt 的文件不可交付。
- **手工编辑信任边界**：native reedit/variant 的具名 receipt 会核 shot plan、全部源素材、输出、profile 与 plan SHA，但最终像素本身不能证明 NLE 时间线。敌对环境要再绑定 timeline/OTIO 或受控导出 runner；不要把产后自签回执描述成密码学 provenance。
- **交付规格按权威分层**：`平台默认 -16 LUFS/-1 dBTP` 是内部数字母版，不冒充平台统一官方值；`广电TVC -23 LUFS/-1 dBTP` 对应 EBU R128 programme recommendation；客户/播出机构书面规格优先并在项目留证。安全区必须按实际 placement 模板，不能从响度 profile 推断。
- **SDR 色彩母版**：BT.709 是本线内部 SDR 交付档；HDR 项目必须有转换/监看/批准证据。`compose_preflight` 查源，`delivery_qc` 查最终文件，二者不能互相替代。

## 接缝处理（治"剪起来跳"）

读 `storyboard.json` 每接缝 `continuity.transition`：硬切裸拼 / 跳变未焊→局部 xfade 微溶解 / 缺空镜→报警不伪造。有意硬切（如反转）不溶解。

## 测试

```bash
cd skills/ad/ad-compose && python3 -m pytest test_cutdown_reframe.py test_accessibility_qc.py test_compose_preflight.py test_rendered_text_qc.py test_provenance_qc.py test_deliver_orchestration.py
```

## 常见错误

| 错误 | 纠正 |
|---|---|
| 占位 VO 直接出成片 | 占位只做 demo；正式片用真 VO 复跑（音画才准）|
| cutdown 机械截前 15s | 按镜头优先级保钩子/产品/CTA 重剪，别砍掉记忆点 |
| cutdown 留数据大字却删来源/免责 | 用同一 `claim_id` 绑定 disclosure；脚本会自动补回或 block |
| 竖版直接拉伸或默认中心裁切 | 先选 placement-native 模式；高风险走原生重编，机械裁切须具名签核 + 当前安全区 + 逐镜焦点 |
| HDR/BT.2020 直接打 BT.709 标签 | 先做显式色彩转换与监看留证；仅改 metadata 会造成色偏/高光错误 |
| 有 VO 却无字幕，或机器说“无闪烁”就放行 | 缺字幕会 block；闪烁扫描只作 WARN，最终仍需具名复核 |
| OCR 找到了文字就当通过 | OCR/视觉模型只定位；逐条记录 observed_text、具名审片、对比度/时长/遮挡确认和证据 |
| `metadata_status=preserve` 就当 C2PA/隐式标识存在 | 必须探测最终文件，或提供绑定当前 SHA 的 c2patool/供应商/平台探测回执 |
| 把 -16 LUFS 写成所有平台官方要求 | 它是内部数字母版；客户/平台书面规格优先，广电参考 EBU R128 -23 LUFS/-1 dBTP |
| 关键 logo/包装文字靠 AI 生 | end card / 包装文字用真素材合成 |
