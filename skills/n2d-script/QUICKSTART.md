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
python3 skills/n2d/progress.py set <作品根> 第N集 剧本改编 ✅
python3 skills/n2d/progress.py set <作品根> 第N集 bgm ✅
python3 skills/n2d/progress.py set <作品根> 第N集 封面 ✅
```

## Stage 2: 分镜设计

Prerequisites:
- `配音` column is complete
- `合成/第N集/配音/时长清单.json` exists

Gate + flow (注意顺序——`validate_timings` 是**定稿后自检**，需要 finalize 先产出 `镜头时长.json`/字幕，别在 Stage 2 一开头就跑它)：
```bash
# ① 占位闸门 + 定稿：用时长清单重定时，产 字幕_中文.srt[+英文] + 镜头时长.json
#    占位配音会被拒绝定稿（rough preview 用 FINALIZE_ALLOW_PLACEHOLDER=1 放行）
python3 skills/n2d-script/finalize_storyboard.py <作品根> 第N集
# ② 写设计文档（分镜剧本.md / 故事板.md / storyboard.json / 素材清单.md）
# ③ 定稿后自检：核对 配音→字幕→镜头时长 链对齐
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
python3 skills/n2d/progress.py set <作品根> 第N集 分镜设计 ✅
python3 skills/n2d/progress.py set <作品根> 第N集 素材清单 ✅
python3 skills/n2d/progress.py set <作品根> 第N集 字幕中 ✅
```

