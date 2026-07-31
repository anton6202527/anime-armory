# 原生音画 opt-in 策略

目标：说明逐镜混合路线如何处理 clip 原生音轨。默认先看 `production_mode_route`：普通、画面先行、旁白后配和 neutral-mouth base plate 走无声流；获批表演轨只作口型条件，模型音轨丢弃；`native_av` 镜才允许原生同步台词+口型+环境声。低风险空镜可 opt-in 环境声。项目级 `原生音画` 仍是显式兼容模式。

## 1. 默认策略

- `视频生成音频策略` 是项目级基础偏好；混合模式逐镜 route 可升级为表演条件或 native AV。
- `视频原生音轨` 约束 compose 如何处理允许保留的音轨：普通/base/performance-condition route 丢弃，低风险环境声可低音量混入，native AV 保留。
- 平台意外给无声 route 返回音轨时，n2d-video 把正式 MP4 规整为无音轨，原片备份到 `生产数据/video_raw_with_audio/`；允许音频的 route 才把原轨交给 compose。

## 2. 允许 opt-in 的镜头

只能选低风险镜头：

- 纯空镜、转场、远景氛围镜头。
- 无口型镜头：背身、侧脸、剪影、人物嘴部不可见。
- 无对白镜头：本 Clip 没有角色台词，也没有需要和字幕对齐的人声。
- 环境声/动作声价值明确：雨、风、火、雷、法术嗡鸣、脚步、破空、门响、水声、 crowd bed。

## 3. 禁止 opt-in 的镜头

以下镜头不得启用原生人声/台词，也不建议混入原生音轨：

- 正面说话特写 / 中近景可见口型。
- 有 n2d-voice 角色台词、旁白、系统音需要精确对齐的镜头。
- 克隆音色/指定角色音色是卖点的镜头。
- 台词信息密集、字幕强绑定、情绪表演依赖配音停顿的镜头。
- 原生音轨里疑似有人声、哼唱、旁白、不可控语言。

## 4. prompt 字段

每个 video Clip 必填：

```markdown
**原生音画策略**：audio_intent=none|ambience|native_sfx；risk=low|medium|high；mouth_visible=yes|no；speech_policy=no_native_speech；compose_policy=丢弃|低音量混入环境声|保留原片音轨；review=生成后确认无原生人声
```

推荐写法：

- 默认：`audio_intent=none; risk=low; mouth_visible=no; speech_policy=no_native_speech; compose_policy=丢弃; generation_flow=video_only/no_audio`
- 环境声 opt-in：`audio_intent=ambience; risk=low; mouth_visible=no; speech_policy=no_native_speech; compose_policy=低音量混入环境声; review=确认仅雨声/风声/火声`
- 原片音轨保留：仅用于无配音预览或纯环境片段，`compose_policy=保留原片音轨`；有 n2d-voice 配音轨时 gate 与 `compose.sh` 都会阻断，除非显式证明配音轨仅为旁白/系统层并用 `ALLOW_NATIVE_AV_VOICEOVER=1` 放行。

> **`mouth_visible` 的真值在哪：就是上面这个 prompt 字段，但必须有 sidecar 证据。** `mouth_detect.py --write` 会读 storyboard 文本启发式（`router.clip_has_mouth_visible`）、首帧 PNG（装 insightface 时）、以及 prompt 里已填的值，三方复核后写 `生产数据/mouth_visible_audit_第N集.json`。冲突时退出码 1，但标准 wrapper 会继续进入 gate，由 gate 结构化阻断。"以图为准"= 由你照 sidecar 建议**改 prompt 里的 `mouth_visible`**，脚本不会替你回写 prompt。下游消费这个 prompt 字段和 sidecar 的是：`router.py`（原生音画 opt-in / 口型路由）、`gate.py --stage video_preflight`（缺 sidecar 或冲突即 BLOCK）、`n2d-score`（风险标记统计）。

## 5. compose 处理

`n2d-compose/compose.sh` 按 `视频原生音轨` 选择点处理：

| 策略 | 行为 |
|---|---|
| `丢弃` | 默认；clip 原生音轨转为空音轨，最终只混 配音 + BGM + SFX |
| `低音量混入环境声` | 抽取 clip 原生音轨，按 `CLIP_AUDIO_GAIN`（默认 0.35）压低混入 |
| `保留原片音轨` | 抽取原生音轨按原音量混入；仅无配音/测试预览/明确保留原片声时使用 |

兼容旧命令：`KEEP_CLIP_AUDIO=1` 等价于 `视频原生音轨=低音量混入环境声`。

## 6. gate 规则

- video prompt 缺 `原生音画策略` 字段即阻断。
- 说话/口型镜、`native_speech`、`lipsync_condition_only`、或任何原生环境声/音效 opt-in 镜，必须有 `生产数据/mouth_visible_audit_第N集.json`；sidecar 里有 warn 时，按建议修 prompt 后重跑。
- `audio_intent=ambience|native_sfx` 或 `compose_policy=低音量混入环境声|保留原片音轨` 时，必须同时满足 `risk=low`、`mouth_visible=no`、`speech_policy=no_native_speech`。
- `_设置.md` 选择 `视频生成音频策略=低风险环境声`、`视频原生音轨=低音量混入环境声` 或 `保留原片音轨` 时，`出视频/第N集/prompt/00_总览.md` 必须有「原生音画 opt-in 清单」，逐 Clip 说明为什么低风险。
- compose 阶段若发现 clip 有音频流且策略为 `保留原片音轨`，同时存在 n2d-voice 配音轨，则阻断，避免双人声。
