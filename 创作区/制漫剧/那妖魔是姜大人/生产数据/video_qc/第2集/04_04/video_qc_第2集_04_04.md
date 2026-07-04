# n2d Video QC

- episode: 第2集
- batch: 04_04
- clips: 1
- contact_sheet: `/Users/lalala/learn/anime-armory/创作区/制漫剧/那妖魔是姜大人/生产数据/video_qc/第2集/04_04/contact_sheet_04_04.jpg`

| Clip | Source MP4 | Duration | Size | Audio | Frames | Notes |
|---|---|---:|---|---|---:|---|
| Clip_04 | `Clip_04_一刀斩虎山神.mp4` | 12.183s | 704x1248 | no | 3 |  |

## Seam machine check（尾帧接力 · 前镜 end 帧 vs 后镜 start 帧）

- checked: 2 · block: 0 · warn: 0

| Seam | dHash | Color dist | Verdict |
|---|---:|---:|---|
| Clip_03 → Clip_04 | 19 | 0.1005 | info |
| Clip_04 → Clip_05 | 23 | 0.0684 | info |

## Anchor adherence（中段锚帧消费对账 · storyboard anchor vs generated sample）

- checked: 3 · block: 0 · warn: 2 · skipped: 0

| Clip | Anchor | Sample | Δs | dHash | Color dist | Verdict |
|---|---|---|---:|---:|---:|---|
| Clip_04 | `出图/第2集/图片/Clip04_a1.png` | mid@6.092 | 2.292 | 25 | 0.0335 | warn |
| Clip_04 | `出图/第2集/图片/Clip04_a3.png` | end@11.983 | 1.583 | 20 | 0.0277 | warn |

Status: pending human review unless the batch manifest marks it accepted.
