# n2d-voice Quickstart

默认流程是“声音选角先行，最终配音后置”，前期只建时间基准，不生成占位 WAV。

前置：

- `脚本/第N集/voiceover.txt` 已存在。
- 若使用克隆/参考音，合规包已登记授权。

## 1. 建立选角表与无 WAV 时间基准

```bash
python3 skills/n2d/n2d-voice/voice_preflight.py prepare <作品根> 第N集
python3 skills/n2d/n2d-script/validate_timings.py <作品根> 第N集
```

输出：

- `设定库/voice_casting.json`
- `合成/第N集/配音/timing_estimate.json`
- `_进度.md` 中 `配音=⏳rough`，表示时间基准就绪，不表示已有粗配音

此步骤保证 `audio_generated=false`，不会创建 `line_NN.wav` 或 `voice_zh.wav`。

## 2. 试听并锁定角色声音

```bash
python3 skills/n2d/n2d-voice/voice_preflight.py lock <作品根> <角色> \
  --backend <后端> --voice-id <音色ID> \
  --canonical-sample <试听样本路径> --approved-by <签收人>
python3 skills/n2d/n2d-voice/voice_preflight.py check <作品根> 第N集 --purpose final
```

只试听少量、覆盖不同情绪的代表台词。选角未锁时，混合模式会阻止批量最终配音。

## 3. 按需生成导引或最终音轨

可信导引轨仅用于确实需要先有表演的可见口型镜头：

```bash
N2D_VOICE_PURPOSE=guide python3 skills/n2d/n2d-voice/render_voice.py <作品根> 第N集 zh
```

它写入 `合成/第N集/配音_导引/`。默认 final：

```bash
python3 skills/n2d/n2d-voice/render_voice.py <作品根> 第N集 zh
```

final 输出 `合成/第N集/配音/line_NN.wav`、`voice_zh.wav`、`时长清单.json`，成功后才把配音列置为 `✅`。真实时长与估时有偏差时，刷新阶段2、OTIO 与受影响的口型 pass；不要用压速掩盖结构变化。

旧项目的 `占位:true` 仍可读取，但不再是新项目默认路径，也不得进入正式成片。
