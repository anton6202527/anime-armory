# n2d-script Quickstart

## Stage 1: 剧本改编

Prerequisites:
- New novel path, or existing `制漫剧/<剧名>/`
- New project must choose `制作模式` once

Command:
```bash
python3 skills/n2d-script/scripts/split_novel.py "<小说路径>" --by-chapter --target 810 --min 540 --max 1080 --limit 3
```

Outputs:
- `脚本/第N集/voiceover.txt`
- `脚本/第N集/bgm.txt`
- `脚本/第N集/封面.md`
- `设定库/global_style.md`
- `设定库/characters/*.md`
- `设定库/locations/*.md`

Progress:
```bash
python3 skills/novel2drama/progress.py set <作品根> 第N集 剧本改编 ✅
python3 skills/novel2drama/progress.py set <作品根> 第N集 bgm ✅
python3 skills/novel2drama/progress.py set <作品根> 第N集 封面 ✅
```

## Stage 2: 分镜设计

Prerequisites:
- `配音` column is complete
- `合成/第N集/配音/时长清单.json` exists

Gate:
```bash
python3 skills/n2d-script/validate_timings.py <作品根> 第N集
```

Required outputs:
- `脚本/第N集/分镜剧本.md`
- `脚本/第N集/故事板.md`
- `脚本/第N集/storyboard.json`
- `脚本/第N集/素材清单.md`
- `脚本/第N集/字幕_中文.srt`
- `脚本/第N集/镜头时长.json`

Progress:
```bash
python3 skills/novel2drama/progress.py set <作品根> 第N集 分镜设计 ✅
python3 skills/novel2drama/progress.py set <作品根> 第N集 素材清单 ✅
python3 skills/novel2drama/progress.py set <作品根> 第N集 字幕中 ✅
```

