# n2d Video QC

- episode: 第1集
- batch: 01_01
- clips: 1
- contact_sheet: `/Users/wesley/learn/anime-armory/创作区/制漫剧/仙界闭关小能手/生产数据/video_qc/第1集/01_01/contact_sheet_01_01.jpg`

| Clip | Source MP4 | Duration | Size | Audio | Frames | Notes |
|---|---|---:|---|---|---:|---|
| Clip_01 | `Clip_01_黑殿全景慢推.mp4` | 4.087s | 720x1280 | yes | 3 |  |

## Seam machine check（尾帧接力 · 前镜 end 帧 vs 后镜 start 帧）

- checked: 1 · block: 0 · warn: 0

| Seam | dHash | Color dist | Verdict |
|---|---:|---:|---|
| Clip_01 → Clip_02 | 31 | 0.0286 | info |

## Anchor adherence（中段锚帧消费对账 · storyboard anchor vs generated sample）

- checked: 1 · block: 0 · warn: 1 · skipped: 0

| Clip | Anchor | Sample | Δs | dHash | Color dist | Verdict |
|---|---|---|---:|---:|---:|---|
| Clip_01 | `出图/第1集/图片/Clip01_mid.png` | mid@2.043 | 0.293 | 15 | 0.122 | warn |

Status: pending human review unless the batch manifest marks it accepted.
