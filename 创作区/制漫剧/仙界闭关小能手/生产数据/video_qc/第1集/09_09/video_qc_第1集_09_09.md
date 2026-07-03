# n2d Video QC

- episode: 第1集
- batch: 09_09
- clips: 1
- contact_sheet: `/Users/wesley/learn/anime-arsenal/创作区/制漫剧/仙界闭关小能手/生产数据/video_qc/第1集/09_09/contact_sheet_09_09.jpg`

| Clip | Source MP4 | Duration | Size | Audio | Frames | Notes |
|---|---|---:|---|---|---:|---|
| Clip_09 | `Clip_09_张老大拍肩落命令.mp4` | 6.084s | 720x1280 | yes | 3 |  |

## Seam machine check（尾帧接力 · 前镜 end 帧 vs 后镜 start 帧）

- checked: 2 · block: 0 · warn: 0

| Seam | dHash | Color dist | Verdict |
|---|---:|---:|---|
| Clip_08 → Clip_09 | 33 | 0.0371 | info |
| Clip_09 → Clip_10 | 37 | 0.0708 | info |

## Anchor adherence（中段锚帧消费对账 · storyboard anchor vs generated sample）

- checked: 1 · block: 0 · warn: 1 · skipped: 0

| Clip | Anchor | Sample | Δs | dHash | Color dist | Verdict |
|---|---|---|---:|---:|---:|---|
| Clip_09 | `出图/第1集/图片/Clip09_mid.png` | mid@3.042 | 0.292 | 28 | 0.0252 | warn |

Status: pending human review unless the batch manifest marks it accepted.
