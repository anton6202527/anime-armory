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
- `出图/common/prompt/00_索引.md`
- shared reference PNGs in `出图/common/`
- `出图/第N集/prompt/00_总览.md`
- `出图/第N集/prompt/01_分镜出图.md`
- shot PNGs in `出图/第N集/`
- required tail-frame PNGs when `storyboard.json continuity.need_endframe=true`

Progress:
```bash
python3 skills/novel2drama/progress.py set <作品根> 第N集 出图prompt ✅
python3 skills/novel2drama/progress.py set <作品根> 第N集 出图 X/Y
```

Notes:
- Default `生图AI` is `Codex only`; do not use Dreamina/即梦 unless `_设置.md` explicitly selects it.
- Shared reference assets must be complete before episode shot PNGs.

