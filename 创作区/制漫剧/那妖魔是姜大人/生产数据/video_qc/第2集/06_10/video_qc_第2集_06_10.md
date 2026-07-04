# n2d Video QC

- episode: 第2集
- batch: 06_10
- clips: 6
- contact_sheet: `/Users/lalala/learn/anime-armory/创作区/制漫剧/那妖魔是姜大人/生产数据/video_qc/第2集/06_10/contact_sheet_06_10.jpg`

| Clip | Source MP4 | Duration | Size | Audio | Frames | Notes |
|---|---|---:|---|---|---:|---|
| Clip_06 | `Clip_06_古卷收虎与道行流逝.mp4` | 11.183s | 704x1248 | no | 3 |  |
| Clip_07_part1 | `Clip_07_猛虎快刀圆满与状态面板_part1.mp4` | 9.017s | 720x1280 | no | 3 |  |
| Clip_07_part2 | `Clip_07_猛虎快刀圆满与状态面板_part2.mp4` | 9.017s | 720x1280 | no | 3 |  |
| Clip_08 | `Clip_08_姜月初读懂长久买卖.mp4` | 9.183s | 704x1248 | no | 3 |  |
| Clip_09 | `Clip_09_替裴合眼与欠命账.mp4` | 12.683s | 704x1248 | no | 3 |  |
| Clip_10 | `Clip_10_官道火把马蹄逼近.mp4` | 5.183s | 704x1248 | no | 3 |  |

## Seam machine check（尾帧接力 · 前镜 end 帧 vs 后镜 start 帧）

- checked: 5 · block: 0 · warn: 0
- note: 部分中段锚帧离 start/mid/end 三采样点太远或 PNG 缺失，锚帧消费对账跳过；必要时加密抽帧复核。

| Seam | dHash | Color dist | Verdict |
|---|---:|---:|---|
| Clip_05 → Clip_06 | 26 | 0.2014 | info |
| Clip_06 → Clip_07 | 32 | 0.0372 | info |
| Clip_07 → Clip_08 | 30 | 0.0461 | info |
| Clip_08 → Clip_09 | 33 | 0.0847 | info |
| Clip_09 → Clip_10 | 21 | 0.1358 | info |

## Intra-clip identity sampling（近景片内身份漂移 · start/mid/end 抽帧）

- closeup clips checked: 4 · block: 0 · warn: 2（warn=粗筛交人判；block=近景非双帧镜结构远超重画阈值 dHash>44，拒绝验收；精确同人判定走 n2d-review/temporal_consistency.analyze）

| Clip | Source MP4 | Lens | Max dHash | Verdict |
|---|---|---|---:|---|
| Clip_07_part1 | `Clip_07_猛虎快刀圆满与状态面板_part1.mp4` | 系统面板特写；INSERT 技能名；MS 英雄低角度；系统状态面板+人物半身 | 38 | warn |
| Clip_07_part2 | `Clip_07_猛虎快刀圆满与状态面板_part2.mp4` | 系统面板特写；INSERT 技能名；MS 英雄低角度；系统状态面板+人物半身 | 39 | warn |

## Anchor adherence（中段锚帧消费对账 · storyboard anchor vs generated sample）

- checked: 5 · block: 0 · warn: 0 · skipped: 1

Status: pending human review unless the batch manifest marks it accepted.
