# n2d Video QC

- episode: 第1集
- batch: 17_17
- clips: 1
- contact_sheet: `/Users/wesley/learn/anime-arsenal/创作区/制漫剧/仙界闭关小能手/生产数据/video_qc/第1集/17_17/contact_sheet_17_17.jpg`

| Clip | Source MP4 | Duration | Size | Audio | Frames | Notes |
|---|---|---:|---|---|---:|---|
| Clip_17 | `Clip_17_空屋硬板床铁碗.mp4` | 5.062s | 720x1280 | yes | 3 |  |

## Seam machine check（尾帧接力 · 前镜 end 帧 vs 后镜 start 帧）

- checked: 2 · block: 0 · warn: 0

| Seam | dHash | Color dist | Verdict |
|---|---:|---:|---|
| Clip_16 → Clip_17 | 19 | 0.1764 | info |
| Clip_17 → Clip_18 | 31 | 0.0601 | info |

## Anchor adherence（中段锚帧消费对账 · storyboard anchor vs generated sample）

- checked: 1 · block: 1 · warn: 0 · skipped: 0

| Clip | Anchor | Sample | Δs | dHash | Color dist | Verdict |
|---|---|---|---:|---:|---:|---|
| Clip_17 | `出图/第1集/图片/Clip17_mid.png` | mid@2.531 | 0.031 | 34 | 0.0579 | block |

Status: pending human review unless the batch manifest marks it accepted.
