# n2d-voice Quickstart

Prerequisites:
- `脚本/第N集/voiceover.txt` exists
- Voice backend credentials or local service are configured if using real voice

Command:
```bash
python3 skills/n2d-voice/render_voice.py <作品根> 第N集 zh
```

Outputs:
- `合成/第N集/配音/line_NN.wav`
- `合成/第N集/配音/voice_zh.wav`
- `合成/第N集/配音/时长清单.json`

Progress:
- `render_voice.py` updates `配音 ✅` automatically.
- Opt out with `N2D_UPDATE_PROGRESS=0`.

Checks:
```bash
python3 skills/n2d-script/validate_timings.py <作品根> 第N集
```

Placeholder policy:
- `占位:true` is acceptable only for rough timing or explicit `先出视频后配音`.
- Formal video/compose gates block placeholder audio.

