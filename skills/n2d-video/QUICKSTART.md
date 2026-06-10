# n2d-video Quickstart

Prerequisites:
- `出图` column is complete
- `脚本/第N集/storyboard.json` exists
- Shot PNGs and any required tail-frame PNGs exist

Gate:
```bash
python3 skills/n2d-dashboard/scripts/dashboard.py gate <作品根> 第N集 --stage video
```

Required outputs:
- `出视频/第N集/prompt/00_总览.md`
- `出视频/第N集/prompt/01_clips.md`
- `出视频/第N集/视频/ClipK_*.mp4`

Progress:
```bash
python3 skills/novel2drama/progress.py ensure-col <作品根> 视频prompt ⬜
python3 skills/novel2drama/progress.py set <作品根> 第N集 视频prompt ✅
python3 skills/novel2drama/progress.py set <作品根> 第N集 视频 X/Y
```

Notes:
- Keep platform-native clip audio in the original MP4; `n2d-compose` decides whether to discard or mix it.
- Every Clip prompt must include `原生音画策略`; only low-risk ambience/SFX clips can opt in, and native speech remains forbidden by default.
- Use backend-specific single-clip duration limits from `references/platforms.md`.
