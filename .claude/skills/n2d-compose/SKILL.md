---
name: n2d-compose
description: Stage 6 of novel2drama (剪映合成的脚本化替代) — assemble a finished episode 成片 from 视频/ clips + (可选)配音轨 + (可选)BGM(占位/文件/Suno) + 烧录双语字幕. Mixes voice with BGM ducking, burns subtitles via Pillow+overlay (本机 ffmpeg 无 libass). Writes _进度.md 成片 column. Use when asked to 合成, 合成成片, 成片, 加BGM, 加背景音乐, 烧字幕, 混音, 出成片, 导出成片. Triggers 合成, 成片, 加BGM, 背景音乐, 烧字幕, 混音, 导出, compose, 剪映.
---

# n2d-compose — 合成成片（剪映那步的脚本化替代）

把一集的 `视频/`(clips) + `配音/voice_*.wav`(可选) + BGM(可选) + 字幕 烧成 `成片_第N集_{mode}.mp4`。

## 核心原则
- **配音先行**：BGM 垫在配音下面并被配音 ducking（先有配音再压 BGM）。配音轨由 n2d-voice 在前置阶段产出，本 skill **只消费不生成**。
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
