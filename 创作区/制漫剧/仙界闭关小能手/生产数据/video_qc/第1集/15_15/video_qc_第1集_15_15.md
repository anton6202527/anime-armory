# n2d Video QC

- episode: 第1集
- batch: 15_15
- clips: 1
- contact_sheet: `/Users/wesley/learn/anime-arsenal/创作区/制漫剧/仙界闭关小能手/生产数据/video_qc/第1集/15_15/contact_sheet_15_15.jpg`

| Clip | Source MP4 | Duration | Size | Audio | Frames | Notes |
|---|---|---:|---|---|---:|---|
| Clip_15 | `Clip_15_贺平生仰看水缸.mp4` | 5.085s | 720x1280 | yes | 3 |  |

## Seam machine check（尾帧接力 · 前镜 end 帧 vs 后镜 start 帧）

- checked: 2 · block: 0 · warn: 0

| Seam | dHash | Color dist | Verdict |
|---|---:|---:|---|
| Clip_14 → Clip_15 | 28 | 0.0049 | info |
| Clip_15 → Clip_16 | 37 | 0.122 | info |

## Anchor adherence（中段锚帧消费对账 · storyboard anchor vs generated sample）

- checked: 1 · block: 0 · warn: 0 · skipped: 0

Status: pending human review unless the batch manifest marks it accepted.
