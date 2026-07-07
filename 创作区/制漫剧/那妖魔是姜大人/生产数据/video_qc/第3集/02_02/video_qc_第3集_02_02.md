# n2d Video QC

- episode: 第3集
- batch: 02_02
- clips: 1
- contact_sheet: `/Users/wesley/learn/anime-armory/创作区/制漫剧/那妖魔是姜大人/生产数据/video_qc/第3集/02_02/contact_sheet_02_02.jpg`

| Clip | Source MP4 | Duration | Size | Audio | Frames | Notes |
|---|---|---:|---|---|---:|---|
| Clip_02 | `Clip_02_搜尸求生：生存物资.mp4` | 12.183s | 704x1248 | no | 3 |  |

## Seam machine check（尾帧接力 · 前镜 end 帧 vs 后镜 start 帧）

- checked: 2 · block: 0 · warn: 0

| Seam | dHash | Color dist | Verdict |
|---|---:|---:|---|
| Clip_01 → Clip_02 | 24 | 0.176 | info |
| Clip_02 → Clip_03 | 19 | 0.0179 | info |

## Anchor adherence（中段锚帧消费对账 · storyboard anchor vs generated sample）

- checked: 1 · block: 0 · warn: 0 · skipped: 0

Status: pending human review unless the batch manifest marks it accepted.
