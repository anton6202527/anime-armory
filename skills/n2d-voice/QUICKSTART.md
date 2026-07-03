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
- `占位:true` is acceptable for rough timing in the default `先出视频后配音` workflow.
- Compose/release still requires real voice or an explicit fitting pass; `配音先行` blocks placeholder audio before paid image/video.
