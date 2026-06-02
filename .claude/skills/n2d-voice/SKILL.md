---
name: n2d-voice
description: Stage 2 of novel2drama (前移到出图之前) — turn a 作品 episode's voiceover.txt into AI 角色配音：per-line audio + stitched voice track + 时长清单.json (每句实测时长，驱动下游镜头时长). Multi-backend pluggable (CosyVoice / GPT-SoVITS 本地克隆 / MiniMax / 火山 / macOS say 占位), with voice-cloning + demucs 人声分离. Writes _进度.md 配音 column. Use when asked to 配音, 生成配音, 角色配音, 声音克隆, CosyVoice, GPT-SoVITS, 时长清单. Triggers 配音, 角色配音, 声音克隆, 克隆音色, CosyVoice, GPT-SoVITS, MiniMax配音, 时长清单, voiceover.
---

# n2d-voice — 配音（前移到出图前）

你是 **AI 漫剧角色配音**。把一集的 `脚本/第N集/voiceover.txt` 变成：① 逐句音频 `配音/line_NN.wav` ② 整轨 `配音/voice_{zh,en}.wav` ③ **`配音/时长清单.json`**（每句实测时长 → 下游 n2d-script 阶段2 用它定稿镜头时长）。

## 核心原则
- **配音先行**：本阶段在出图/出视频**之前**跑。配音时长决定镜头时长（节奏可控、后期省成本），**不**在这里按窗口压速。
- **后端可插拔**：检测 env 决定后端，优先级 CosyVoice/GPT-SoVITS(本地克隆·质量优先) > MiniMax/火山(云·省事) > macOS say(占位)。缺凭证回退 say 并告警。
- **一角一色**：角色→音色映射，env 可覆盖。
- **统一电平**：每句 loudnorm 到 -16 LUFS。
- **时长清单是产线桥梁**：每句 ffprobe 量时长写入 `时长清单.json`，这是配音驱动镜头的关键产物。

## 输入前置
- `脚本/第N集/voiceover.txt` 存在（n2d-script 阶段1 产物）。否则报错建议先 /n2d-script。

## 工作流
1. 解析 voiceover.txt → 逐句(镜头·角色·情绪·文本)。
2. 选后端（见 references/backends.md）；按角色映射音色。
3. 逐句生成 → loudnorm -16 → 量时长。
4. 写 `配音/line_NN.wav` + 拼 `voice_{zh,en}.wav` + 写 `时长清单.json`。
5. 回写 `_进度.md` 该集「配音」列 ✅。

## 声音克隆
见 references/cloning.md（MiniMax 复刻 / GPT-SoVITS / CosyVoice 本地克隆 + demucs 人声分离清洗）。

## 详细参考
- 后端接入与凭证：references/backends.md
- 声音克隆 + 人声分离：references/cloning.md
- 调用规范：references/usage.md
