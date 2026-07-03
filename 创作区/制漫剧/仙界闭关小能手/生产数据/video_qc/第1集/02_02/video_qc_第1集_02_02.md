# n2d Video QC

- episode: 第1集
- batch: 02_02
- clips: 1
- contact_sheet: `/Users/wesley/learn/anime-armory/创作区/制漫剧/仙界闭关小能手/生产数据/video_qc/第1集/02_02/contact_sheet_02_02.jpg`

| Clip | Source MP4 | Duration | Size | Audio | Frames | Notes |
|---|---|---:|---|---|---:|---|
| Clip_02 | `Clip_02_张老大问年龄.mp4` | 4.087s | 720x1280 | yes | 3 |  |

## Seam machine check（尾帧接力 · 前镜 end 帧 vs 后镜 start 帧）

- checked: 2 · block: 0 · warn: 0

| Seam | dHash | Color dist | Verdict |
|---|---:|---:|---|
| Clip_01 → Clip_02 | 31 | 0.0286 | info |
| Clip_02 → Clip_03 | 27 | 0.0466 | info |

## Intra-clip identity sampling（近景片内身份漂移 · start/mid/end 抽帧）

- closeup clips checked: 1 · block: 0 · warn: 1（warn=粗筛交人判；block=近景非双帧镜结构远超重画阈值 dHash>44，拒绝验收；精确同人判定走 n2d-review/temporal_consistency.analyze）

| Clip | Source MP4 | Lens | Max dHash | Verdict |
|---|---|---|---:|---|
| Clip_02 | `Clip_02_张老大问年龄.mp4` | 中近景·低角度 | 36 | warn |

## Anchor adherence（中段锚帧消费对账 · storyboard anchor vs generated sample）

- checked: 1 · block: 0 · warn: 1 · skipped: 0

| Clip | Anchor | Sample | Δs | dHash | Color dist | Verdict |
|---|---|---|---:|---:|---:|---|
| Clip_02 | `出图/第1集/图片/Clip02_mid.png` | mid@2.043 | 0.293 | 23 | 0.0061 | warn |

Status: pending human review unless the batch manifest marks it accepted.
