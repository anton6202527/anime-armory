# n2d Video QC

- episode: 第1集
- batch: 04_04
- clips: 1
- contact_sheet: `创作区/制漫剧/那妖魔是姜大人/生产数据/video_qc/第1集/04_04/contact_sheet_04_04.jpg`

| Clip | Source MP4 | Duration | Size | Audio | Frames | Notes |
|---|---|---:|---|---|---:|---|
| Clip_04 | `Clip_04_被迫扶裴南行.mp4` | 10.183s | 704x1248 | no | 3 |  |

## Seam machine check（尾帧接力 · 前镜 end 帧 vs 后镜 start 帧）

- checked: 2 · block: 0 · warn: 0

| Seam | dHash | Color dist | Verdict |
|---|---:|---:|---|
| Clip_03 → Clip_04 | 43 | 0.1694 | info |
| Clip_04 → Clip_05 | 30 | 0.2502 | info |

## Anchor adherence（中段锚帧消费对账 · storyboard anchor vs generated sample）

- checked: 1 · block: 0 · warn: 1 · skipped: 0

| Clip | Anchor | Sample | Δs | dHash | Color dist | Verdict |
|---|---|---|---:|---:|---:|---|
| Clip_04 | `出图/第1集/图片/Clip04_mid.png` | mid@5.092 | 1.092 | 19 | 0.008 | warn |

Status: pending human review unless the batch manifest marks it accepted.
