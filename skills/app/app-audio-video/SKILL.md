---
name: app-audio-video
description: 独立的画布音频生视频工作台，读取上传或画布引用的音频，建立时长、节拍、段落和能量时间线，设计视觉连续性与卡点规则，输出可续跑的视频任务并登记验收。Use when a user clicks 音频生视频, 音乐卡点视频, audio-to-video, beat-synced video, or needs the LibTV-style audio import → beat/visual plan → video generation flow. This top-level skill must not import, invoke, or depend on mv, mv-beat, mv-video, song, or any series implementation.
---

# app-audio-video

把“音频生视频”作为独立工作台执行；它不是 MV 生产线的快捷入口，也不读取任何系列项目状态。

## 独立边界

- 只运行本目录 `scripts/audio_video.py`，仅使用 Python 标准库。
- 不 import、调用或复制任何系列的节拍、分镜、视频、合成或设置实现。
- 可以学习卡点和音画连续性原则，但本 skill 自带状态、schema、分析结果和 job。
- 输入输出只通过显式文件交接；无分析依赖或生成后端时仍输出可编辑草案与可续跑 job 包。

## 工作流

### 1. 导入音频

接受 WAV 或其它音频文件。WAV 用标准库读取真实时长；其它格式保留文件 SHA，并要求用户或后端补充时长，不伪造分析成功。

### 2. 节拍与画面

1. 建立可编辑段落和卡点时间线；自动分析不可用时生成等距候选并标记 `estimated`。
2. 选择上传、当前画布或文字描述作为视觉起点。
3. 确认视觉风格、主体连续性、切镜强度、运镜与禁止变化项。

### 3. 生成与验收

1. 分列视频模型与访问渠道，设置比例、分辨率、时长策略和生成数量。
2. `prepare` 生成绑定音频 SHA 和时间线 SHA 的 job。
3. 真实付费生成前确认；无后端时保留 job。
4. 机器结果只到 `machine_complete`；读取当前视频文件并核 SHA，核对节拍、段落、连续性和音轨后，由具名真人以带时区、精确绑定当前字节的显式回执接受才完成。

## AI 代理交互节点

- 自动把音频段落与能量变化转成画面和切镜建议，不让用户填写逐秒表格。
- 风格或主体缺失时只问最影响整体视觉的一项，其余生成可编辑默认。
- 付费提交、覆盖验收结果、替换音频或改用新模型时停下确认。

## 命令

```bash
python3 skills/app/app-audio-video/scripts/audio_video.py init \
  --audio track.wav --output track.audio-video.json

python3 skills/app/app-audio-video/scripts/audio_video.py prepare \
  track.audio-video.json --write

python3 skills/app/app-audio-video/scripts/audio_video.py validate \
  track.audio-video.json

python3 skills/app/app-audio-video/scripts/audio_video.py accept-output \
  track.audio-video.json --reviewer "具名审核人" \
  --statement "我已查看当前视频并接受这些确切字节" \
  --confirm-current-artifact --write
```

`accept-output` 必须由真人触发；runner/agent 不得代填 reviewer 或 confirmation。

字段与完成条件见 [audio-video-schema.md](references/audio-video-schema.md)。
