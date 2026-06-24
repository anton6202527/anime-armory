# n2d-script Quickstart

## Stage 1: 剧本改编

Prerequisites:
- New novel path, or existing `创作区/制漫剧/<剧名>/`
- New project must choose `制作模式` once

Command:
```bash
python3 skills/n2d-script/scripts/split_novel.py "<小说路径>" --by-chapter --limit 3
# 中段开工：先补 `设定库/中段开工前情资产包.md`；用户只给模糊剧情点时，先读章节/关键词定位章号再传参
python3 skills/n2d-script/scripts/split_novel.py "<小说路径>" --by-chapter --start-chapter 48 --limit 3
# 边界词典按 _设置.md `题材` 自动切换（古装爽文/女频情感/悬疑/都市）
# 拆集骨架体检（逐集边界 + 剧级追更骨架：弱钩集群/无闭环/卡点定位，按 `变现模式`）：
python3 skills/n2d-script/scripts/boundary_audit.py <作品根>
# 建卡后：跨集角色形象生命周期预扫（年龄/换装/形态里程碑）→ 人确认
python3 skills/n2d-script/scripts/lifecycle_scan.py <作品根> --write
```

Outputs:
- `脚本/第N集/voiceover.txt`
- `脚本/第N集/bgm.txt`
- `脚本/第N集/封面.md`
- `设定库/global_style.md`
- `设定库/characters/*.md`（含 `_生命周期.md` 跨集形象时间线）
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
# ③ 定稿后自检（闸门）：核对 配音→字幕→镜头时长 链对齐
python3 skills/n2d-script/validate_timings.py <作品根> 第N集
# ④ 集内留存节拍体检（report-only·不替代上面的闸门）：钩子间隔/≥1反转/集尾断点/情绪×信息回报
python3 skills/n2d-script/scripts/beat_audit.py <作品根> 第N集
python3 skills/n2d-script/scripts/beat_audit.py <作品根> --series   # 量产抽检套路同质化
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
