# n2d Video QC

- episode: 第1集
- batch: 11_11
- clips: 1
- contact_sheet: `/Users/wesley/learn/anime-arsenal/创作区/制漫剧/仙界闭关小能手/生产数据/video_qc/第1集/11_11/contact_sheet_11_11.jpg`

| Clip | Source MP4 | Duration | Size | Audio | Frames | Notes |
|---|---|---:|---|---|---:|---|
| Clip_11 | `Clip_11_父母亡故资源被抢.mp4` | 6.084s | 720x1280 | yes | 3 |  |

## Seam machine check（尾帧接力 · 前镜 end 帧 vs 后镜 start 帧）

- checked: 2 · block: 0 · warn: 0

| Seam | dHash | Color dist | Verdict |
|---|---:|---:|---|
| Clip_10 → Clip_11 | 36 | 0.0413 | info |
| Clip_11 → Clip_12 | 30 | 0.0111 | info |

## Anchor adherence（中段锚帧消费对账 · storyboard anchor vs generated sample）

- checked: 1 · block: 1 · warn: 0 · skipped: 0

| Clip | Anchor | Sample | Δs | dHash | Color dist | Verdict |
|---|---|---|---:|---:|---:|---|
| Clip_11 | `出图/第1集/图片/Clip11_mid.png` | mid@3.042 | 0.042 | 36 | 0.0575 | block |

Status: pending human review unless the batch manifest marks it accepted.
