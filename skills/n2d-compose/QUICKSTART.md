# n2d-compose Quickstart

Prerequisites:
- `出视频/第N集/视频/*.mp4` exists
- `脚本/第N集/字幕_中文.srt` exists
- Real voice exists unless this is an explicit rough preview

Gate:
```bash
python3 skills/n2d-dashboard/scripts/dashboard.py gate <作品根> 第N集 --stage compose
```

Command:
```bash
bash skills/n2d-compose/compose.sh <作品根> 第N集 zh
```

With real BGM:
```bash
BGMFILE=/path/to/music.mp3 bash skills/n2d-compose/compose.sh <作品根> 第N集 zh
```

Native clip audio:
```bash
VIDEO_NATIVE_AUDIO_POLICY=低音量混入环境声 bash skills/n2d-compose/compose.sh <作品根> 第N集 zh
```
Only use this after n2d-video has marked the clips as low-risk ambience/SFX with no native speech. Default is `丢弃`.

Outputs:
- `合成/第N集/成片_第N集_zh.mp4`

Progress:
- `compose.sh` updates `成片 ✅` automatically after successful output.
- Opt out with `N2D_UPDATE_PROGRESS=0`.

Final QA:
```bash
python3 skills/n2d-review/scripts/mechanical_check.py <作品根> 第N集
python3 skills/n2d-dashboard/scripts/dashboard.py gate <作品根> 第N集 --stage review
```
