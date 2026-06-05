---
name: n2d-compose
description: Stage 6 of novel2drama (剪映合成的脚本化替代) — assemble a finished episode 成片 from 视频/ clips + (可选)配音轨 + (可选)BGM(占位/文件/Suno) + 烧录双语字幕. Mixes voice with BGM ducking, burns subtitles via Pillow+overlay (本机 ffmpeg 无 libass). Writes _进度.md 成片 column. Use when asked to 合成, 合成成片, 成片, 加BGM, 加背景音乐, 烧字幕, 混音, 出成片, 导出成片. Triggers 合成, 成片, 加BGM, 背景音乐, 烧字幕, 混音, 导出, compose, 剪映.
---

# n2d-compose — 合成成片（剪映那步的脚本化替代）

把一集的 `视频/`(clips) + `配音/voice_*.wav`(可选) + BGM(可选) + 字幕 烧成 `成片_第N集_{mode}.mp4`。

## 偏好（私有 · 用户选择，不写死在本 skill）

本 skill 的可选项**不写死在源码里**。按 `../_偏好约定.md` 读用户私有选择：先读 `<作品根>/_设置.md`；缺则用全局默认 `创作偏好-默认.md` 预填并告知一句；再缺则**首次问一次**→写回 `_设置.md`→同项目之后**沉默沿用**（合规/不可逆/花钱多的点每次仍确认）。

本 skill 涉及的选择点：`BGM来源`、`画幅`。

## 核心原则
- **剪辑节奏 = 不许等长化**（`novel2drama/references/导演节奏.md §四/§五`）：clip 的时长曲线就是剪辑节奏，由上游（配音时长 + 故事板节奏注记）设计好——铺垫长镜、爽点碎切、爽点后留白。本 skill **按原时长拼接（concat -c copy），绝不把 clip 拉成等长**，否则节奏塌成 PPT。
- **卡点**：爽点的冲击 = 画面 + 声音同一帧砸下。用 `BGM_OFFSET` 平移 BGM，让 drop/炸点落在 `故事板.md` 标的爽点时间戳（如 `💥爽点 @ 0:48`）那一帧；反转/觉醒处铺 bgm.txt 标的"重音"音效。
- **留白呼吸**：爆发后那个 `留白·定格` clip 不要被音效填满——让它喘一口（必要时 BGM 瞬时拉低再起）。
- **配音先行**：BGM 垫在配音下面并被配音 ducking（先有配音再压 BGM）。配音轨由 n2d-voice 在前置阶段产出，本 skill **只消费不生成**。
- **clip 原生音频处理（2026 新坑）**：Veo 3.1 / Seedance 2.0 出的 clip 可能**自带原生音轨**（环境音甚至台词）。混音默认策略：**转码时 `-an` 剥掉 clip 原生音轨**（否则与 n2d-voice 配音轨双人声打架），音频全部由 配音+BGM+SFX 这条受控链路提供。若确实要保留环境音底，显式设 `KEEP_CLIP_AUDIO=1`，脚本会低音量混入；不要默认保留。
- **字幕烧录**：本机 Homebrew ffmpeg **无 libass**（无 subtitles/drawtext 滤镜）→ 用 Pillow 把 SRT 渲染成透明 PNG 再 overlay 烧录（render_subs.py）。
- **占位 BGM 为主**：默认程序化占位；可选真实文件覆盖。

## 输入前置
- `出视频/第N集/视频/` 有 clip MP4（n2d-video 产物）。否则报错建议先 /n2d-video。
- `出视频/第N集/配音/voice_{zh,en}.wav`（n2d-voice 产物，可选；无则纯 BGM+字幕）。
- `脚本/第N集/字幕_{中文,英文}.srt`。

## 加 BGM —— 给用户更丰富选项 + 接受自定义
到 BGM 环节，提示用户：
> 「BGM 怎么来？ⓐ 你用 Suno 生成一条给我文件 ⓑ 素材库选 ⓒ 指定本地文件 ⓓ 占位合成。也可以直接说你的想法（循环某首/某风格/某时长），我**鉴定合理可行**(文件存在/格式/时长够循环/版权)后按你的来；不可行说明原因给替代。」
用户给文件 → `BGMFILE=<路径>`；否则占位。

## 转场音效（可选层）
clip 已带即梦原生音效。额外「2~5 个转场音效」做成可选：用户给 SFX 文件就在 clip 边界铺，不给跳过。

## 行业参考（决定音频时展示给用户）
> 对于 90 秒左右的一集漫剧，很多工作室会准备：
> - 1 条背景音乐（全程循环）
> - 2~5 个转场音效
> - AI 角色配音

## 工作流
1. 归集 `视频/` clips → 统一 1080x1920/30fps → 拼接。
2. BGM：`BGMFILE` 文件(loop/trim+fade) 或 程序化占位。
3. 混音：配音(若有) + ducking BGM + clip 自带音效底。
4. 烧字幕（render_subs.py，模式 zh/en/bilingual）。
5. 输出 `成片_第N集_{mode}.mp4`；回写 `_进度.md` 成片列。

## 调用
见 references/usage.md。
