# n2d Video QC

- episode: 第2集
- batch: 07_07
- clips: 1
- contact_sheet: `/Users/lalala/learn/anime-armory/创作区/制漫剧/那妖魔是姜大人/生产数据/video_qc/第2集/07_07/contact_sheet_07_07.jpg`

| Clip | Source MP4 | Duration | Size | Audio | Frames | Notes |
|---|---|---:|---|---|---:|---|
| Clip_07_part2 | `Clip_07_猛虎快刀圆满与状态面板_part2.mp4` | 9.017s | 720x1280 | no | 3 |  |

## Seam machine check（尾帧接力 · 前镜 end 帧 vs 后镜 start 帧）

- checked: 2 · block: 0 · warn: 0

| Seam | dHash | Color dist | Verdict |
|---|---:|---:|---|
| Clip_06 → Clip_07 | 32 | 0.0372 | info |
| Clip_07 → Clip_08 | 30 | 0.0461 | info |

## Intra-clip identity sampling（近景片内身份漂移 · start/mid/end 抽帧）

- closeup clips checked: 1 · block: 0 · warn: 1（warn=粗筛交人判；block=近景非双帧镜结构远超重画阈值 dHash>44，拒绝验收；精确同人判定走 n2d-review/temporal_consistency.analyze）

| Clip | Source MP4 | Lens | Max dHash | Verdict |
|---|---|---|---:|---|
| Clip_07_part2 | `Clip_07_猛虎快刀圆满与状态面板_part2.mp4` | 系统面板特写；INSERT 技能名；MS 英雄低角度；系统状态面板+人物半身 | 39 | warn |

Status: pending human review unless the batch manifest marks it accepted.
