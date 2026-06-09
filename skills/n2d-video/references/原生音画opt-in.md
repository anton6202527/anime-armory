# 原生音画 opt-in 策略

目标：默认继续走 **配音先行 + 受控混音**；只对低风险镜头允许 Veo / Seedance / Kling 等后端的原生环境声或音效参与成片。原生台词/旁白默认仍禁，避免和 n2d-voice 配音双人声、音色漂移、字幕不同步。

## 1. 默认策略

- `_设置.md` 的 `视频原生音轨` 默认是 `丢弃`。
- n2d-video 阶段拿回平台原片，保留 MP4 原生音轨，不提前 `-an` 覆盖。
- n2d-compose 是唯一处理原生音轨的阶段：默认丢弃；opt-in 后才低音量混入环境声或保留原片音轨。

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

- 默认：`audio_intent=none; risk=low; mouth_visible=no; speech_policy=no_native_speech; compose_policy=丢弃`
- 环境声 opt-in：`audio_intent=ambience; risk=low; mouth_visible=no; speech_policy=no_native_speech; compose_policy=低音量混入环境声; review=确认仅雨声/风声/火声`
- 原片音轨保留：仅用于无配音预览或纯环境片段，`compose_policy=保留原片音轨`；有 n2d-voice 配音轨时 gate 会阻断或要求改回低音量混入。

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
- `audio_intent=ambience|native_sfx` 或 `compose_policy=低音量混入环境声|保留原片音轨` 时，必须同时满足 `risk=low`、`mouth_visible=no`、`speech_policy=no_native_speech`。
- `_设置.md` 选择 `低音量混入环境声` 或 `保留原片音轨` 时，`出视频/第N集/prompt/00_总览.md` 必须有「原生音画 opt-in 清单」，逐 Clip 说明为什么低风险。
- compose 阶段若发现 clip 有音频流且策略为 `保留原片音轨`，同时存在 n2d-voice 配音轨，则阻断，避免双人声。
