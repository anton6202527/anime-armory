# n2d-image Quickstart

Prerequisites:
- `分镜设计 ✅`
- `脚本/第N集/storyboard.json` exists
- `脚本/第N集/素材清单.md` exists

Gate:
```bash
python3 skills/n2d-review/scripts/gate.py <作品根> 第N集 --stage image
```

Required outputs:
- `出图/共享/prompt/00_索引.md`
- shared reference PNGs in `出图/共享/图片/`
- `出图/第N集/prompt/00_总览.md`
- `出图/第N集/prompt/01_分镜出图.md`
- shot PNGs in `出图/第N集/图片/`
- required tail-frame PNGs when `storyboard.json continuity.need_endframe=true`

Progress:
```bash
python3 skills/novel2drama/progress.py set <作品根> 第N集 出图prompt ✅
python3 skills/novel2drama/progress.py set <作品根> 第N集 出图 X/Y
```

Notes:
- `生图AI` is a choice point (default `Codex`). 阶段1 allows official multi-reference backends (Seedream / Kling 主体库 / Nano Banana / Sora Cameo). The gate blocks only ① backend MIXING within a project and ② reverse-engineered/unauthorized image paths (即梦/Dreamina 逆向 CLI/web). Pick ONE official backend per project; official Seedream API ≠ 即梦逆向出图.
- Shared reference assets must be complete before episode shot PNGs.
