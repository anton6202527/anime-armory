# n2d-review Quickstart

Stage gates:
```bash
python3 skills/n2d-dashboard/scripts/dashboard.py gate <作品根> 第N集 --stage image_preflight
python3 skills/n2d-dashboard/scripts/dashboard.py gate <作品根> 第N集 --stage image
python3 skills/n2d-dashboard/scripts/dashboard.py gate <作品根> 第N集 --stage video_preflight
python3 skills/n2d-dashboard/scripts/dashboard.py gate <作品根> 第N集 --stage video
python3 skills/n2d-dashboard/scripts/dashboard.py gate <作品根> 第N集 --stage compose
python3 skills/n2d-dashboard/scripts/dashboard.py gate <作品根> 第N集 --stage review
```

Use `image_preflight` / `video_preflight` before paid backend calls; use `image` / `video` after generated assets are landed.

Mechanical QA:
```bash
python3 skills/n2d-review/scripts/mechanical_check.py <作品根> 第N集
python3 skills/n2d-review/scripts/mechanical_check.py <作品根> 第N集 --json
```

What is deterministic:
- subtitles vs voice manifest
- placeholder voice
- `storyboard.json` continuity
- required tail-frame PNGs
- clip count and native audio streams
- rough clip duration consistency
- final watermark presence

What still needs human/LLM judgment:
- face drift
- scene drift
- composition and lens grammar
- pacing feel
- lip sync
- whether native audio contains usable ambience or unwanted speech
