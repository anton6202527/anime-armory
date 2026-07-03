# n2d Video QC

- episode: 第1集
- batch: 12_12
- clips: 1
- contact_sheet: `/Users/wesley/learn/anime-arsenal/创作区/制漫剧/仙界闭关小能手/生产数据/video_qc/第1集/12_12/contact_sheet_12_12.jpg`

| Clip | Source MP4 | Duration | Size | Audio | Frames | Notes |
|---|---|---:|---|---|---:|---|
| Clip_12 | `Clip_12_江剑背影送往秀竹峰.mp4` | 5.085s | 720x1280 | yes | 3 |  |

## Seam machine check（尾帧接力 · 前镜 end 帧 vs 后镜 start 帧）

- checked: 2 · block: 0 · warn: 0

| Seam | dHash | Color dist | Verdict |
|---|---:|---:|---|
| Clip_11 → Clip_12 | 30 | 0.0111 | info |
| Clip_12 → Clip_13 | 26 | 0.0675 | info |

## Anchor adherence（中段锚帧消费对账 · storyboard anchor vs generated sample）

- checked: 1 · block: 0 · warn: 0 · skipped: 0

Status: pending human review unless the batch manifest marks it accepted.
