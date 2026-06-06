---
name: n2d-voice
description: Stage 2 of novel2drama (前移到出图之前) — turn a 作品 episode's voiceover.txt into AI 角色配音：per-line audio + stitched voice track + 时长清单.json (每句实测时长，驱动下游镜头时长). Multi-backend pluggable (CosyVoice / GPT-SoVITS 本地克隆 / MiniMax / 火山 / macOS say 占位), with voice-cloning + demucs 人声分离. Writes _进度.md 配音 column. Use when asked to 配音, 生成配音, 角色配音, 声音克隆, CosyVoice, GPT-SoVITS, 时长清单. Triggers 配音, 角色配音, 声音克隆, 克隆音色, CosyVoice, GPT-SoVITS, MiniMax配音, 时长清单, voiceover.
---

# n2d-voice — 配音（前移到出图前）

你是 **AI 漫剧角色配音**。把一集的 `脚本/第N集/voiceover.txt` 变成：① 逐句音频 `配音/line_NN.wav` ② 整轨 `配音/voice_{zh,en}.wav` ③ **`配音/时长清单.json`**（每句实测时长 → 下游 n2d-script 阶段2 用它定稿镜头时长）。

## 偏好（私有 · 用户选择，不写死在本 skill）

本 skill 的可选项**不写死在源码里**。按 `../_偏好约定.md` 读用户私有选择：先读 `<作品根>/_设置.md`；缺则用全局默认 `创作偏好-默认.md` 预填并告知一句；再缺则**首次问一次**→写回 `_设置.md`→同项目之后**沉默沿用**（合规/不可逆/花钱多的点每次仍确认）。

本 skill 涉及的选择点：`配音后端`、`制作模式`（决定本步在出视频之前还是之后跑真实配音·见下）。

## 核心原则
- **配音先行**：本阶段在出图/出视频**之前**跑。配音时长决定镜头时长（节奏可控、后期省成本），**不**在这里按窗口压速。
- **醒目提示：macOS `say` 中文可能输出空音频**：若 `say` 生成的中文音频无有效 duration，`render_voice.py` 会**自动降级为静音占位时长轨**（按文本长度/语速/钩子估算每句时长，写 `line_NN.wav` / `voice_zh.wav` / `时长清单.json`，并在 manifest 标 `占位:true`、写 `_占位说明.md`）。这不是有声朗读，只能用于 rough timing。
- **占位分阶段（关键）**：macOS `say` 占位**只服务"出图之前"的环节**（跑通流程 / 字幕初定时 / 节奏 rough 预览）。**跨过出图这道线之前，必须换成接近成片的真实配音**（CosyVoice/克隆/MiniMax）定稿时长——因为**占位时长 ≠ 真实配音时长**，用占位时长去驱动出图/出视频（贵），等换真音色时长一变，镜头就要重切 → 白出。占位回退时**显式告警**："当前为占位音色，出图前请换真实配音重定时"。
- **`制作模式`=`先出视频后配音`（快速 demo·不推荐）时本步跑两次**（见 novel2drama SKILL「制作模式」节，必向用户复述不推荐理由）：第一次（出图前）只出**占位/估算 `时长清单.json`** 当时间脚手架，**不追求音质**；真实配音第二次跑（**出视频之后、合成之前**）。这条路把"占位时长驱动出图/出视频"的返工风险显式留给了用户——能跑通但音画大概率对不准。`配音先行`（默认）永远在出图前就出真实配音，本步只跑一次。
- **念白是表演，不是平读**：voiceover.txt 每句的 `情绪/语速/停顿/钩子` 标注**会驱动 TTS**（不是注释）——这是留存的一部分，见 `novel2drama/references/导演节奏.md §六`。
- **后端可插拔**：检测 env 决定后端，优先级 CosyVoice/GPT-SoVITS(本地克隆·质量优先) > MiniMax/火山(云·省事) > macOS say(占位)。缺凭证回退 say 并告警。
- **一角一色**：角色→音色映射，env 可覆盖。
- **统一电平**：每句 loudnorm 到 -16 LUFS。
- **时长清单是产线桥梁**：每句 ffprobe 量时长写入 `时长清单.json`，这是配音驱动镜头的关键产物。

## 表演指导（情绪/语速/停顿/钩子 → 念白）
`render_voice.py` 解析 voiceover.txt 的 `[镜头N·角色·情绪·(语速)] 台词 (钩子)`，落实到念白：

| 标注 | 解析 | 落到 TTS |
|---|---|---|
| **情绪** | 归类成 angry/fearful/sad/happy/serious/neutral（关键词匹配，兼容旧自由词） | **覆盖角色默认 emotion**（MiniMax 走情绪集；火山保角色情绪更保守） |
| **语速 快/慢** | ×1.10 / ×0.90 | 叠到角色基速（clamp 0.7~1.5）；say 后端体现在 rate |
| **停顿 `||`** | 替换成逗号 | TTS 自然气口（反转词前留一拍） |
| **钩子 ⚡/💥/🪝** | 从念白文本剥掉（不念出来），记进 `时长清单.json` 的 `钩子` 字段 | 句后留"悬念呼吸"拍：hook 0.6s / 爽点 0.7s / 集尾 1.0s（env `GAP_HOOK/GAP_CLIMAX/GAP_END` 可调，常规句 `LINE_GAP` 0.4s） |

> 情绪只标自由词（旧格式）也能跑——按关键词归类，归不到就 neutral。要"导演级念白"，按 formats §6 标全情绪+语速+停顿+钩子。`时长清单.json` 新增 `情绪`/`钩子` 字段，供下游分镜/卡点参考。

## 输入前置
- `脚本/第N集/voiceover.txt` 存在（n2d-script 阶段1 产物）。否则报错建议先 /n2d-script。

## 工作流
1. 解析 voiceover.txt → 逐句(镜头·角色·情绪·文本)。
2. 选后端（见 references/backends.md）；按角色映射音色。
3. 逐句生成 → loudnorm -16 → 量时长。若 macOS `say` 中文为空音频,自动生成静音占位轨并告警。
4. 写 `配音/line_NN.wav` + 拼 `voice_{zh,en}.wav` + 写 `时长清单.json`。
5. 回写 `_进度.md` 该集「配音」列 ✅。

## 声音克隆
见 references/cloning.md（MiniMax 复刻 / GPT-SoVITS / CosyVoice 本地克隆 + demucs 人声分离清洗）。

## 详细参考
- 后端接入与凭证：references/backends.md
- 声音克隆 + 人声分离：references/cloning.md
- 调用规范：references/usage.md
