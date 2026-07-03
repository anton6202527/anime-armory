# n2d Video QC

- episode: 第1集
- batch: 19_19
- clips: 1
- contact_sheet: `/Users/wesley/learn/anime-arsenal/创作区/制漫剧/仙界闭关小能手/生产数据/video_qc/第1集/19_19/contact_sheet_19_19.jpg`

| Clip | Source MP4 | Duration | Size | Audio | Frames | Notes |
|---|---|---:|---|---|---:|---|
| Clip_19 | `Clip_19_挑水动作蒙太奇.mp4` | 7.082s | 720x1280 | yes | 3 |  |

## Seam machine check（尾帧接力 · 前镜 end 帧 vs 后镜 start 帧）

- checked: 2 · block: 0 · warn: 0

| Seam | dHash | Color dist | Verdict |
|---|---:|---:|---|
| Clip_18 → Clip_19 | 36 | 0.0836 | info |

## Anchor adherence（中段锚帧消费对账 · storyboard anchor vs generated sample）

- checked: 1 · block: 1 · warn: 0 · skipped: 0

| Clip | Anchor | Sample | Δs | dHash | Color dist | Verdict |
|---|---|---|---:|---:|---:|---|
| Clip_19 | `出图/第1集/图片/Clip19_mid.png` | mid@3.541 | 0.041 | 32 | 0.0596 | block |

Status: pending human review unless the batch manifest marks it accepted.
