# n2d Video QC

- episode: 第1集
- batch: 16_16
- clips: 1
- contact_sheet: `/Users/wesley/learn/anime-armory/创作区/制漫剧/仙界闭关小能手/生产数据/video_qc/第1集/16_16/contact_sheet_16_16.jpg`

| Clip | Source MP4 | Duration | Size | Audio | Frames | Notes |
|---|---|---:|---|---|---:|---|
| Clip_16 | `Clip_16_韩老三交钥匙铁索.mp4` | 5.085s | 720x1280 | yes | 3 |  |

## Seam machine check（尾帧接力 · 前镜 end 帧 vs 后镜 start 帧）

- checked: 2 · block: 0 · warn: 0

| Seam | dHash | Color dist | Verdict |
|---|---:|---:|---|
| Clip_15 → Clip_16 | 37 | 0.122 | info |
| Clip_16 → Clip_17 | 38 | 0.2933 | info |

## Anchor adherence（中段锚帧消费对账 · storyboard anchor vs generated sample）

- checked: 1 · block: 0 · warn: 1 · skipped: 0

| Clip | Anchor | Sample | Δs | dHash | Color dist | Verdict |
|---|---|---|---:|---:|---:|---|
| Clip_16 | `出图/第1集/图片/Clip16_mid.png` | mid@2.543 | 0.293 | 29 | 0.0389 | warn |

Status: pending human review unless the batch manifest marks it accepted.
