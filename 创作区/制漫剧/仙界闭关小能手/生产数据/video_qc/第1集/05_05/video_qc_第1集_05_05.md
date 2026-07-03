# n2d Video QC

- episode: 第1集
- batch: 05_05
- clips: 1
- contact_sheet: `/Users/wesley/learn/anime-armory/创作区/制漫剧/仙界闭关小能手/生产数据/video_qc/第1集/05_05/contact_sheet_05_05.jpg`

| Clip | Source MP4 | Duration | Size | Audio | Frames | Notes |
|---|---|---:|---|---|---:|---|
| Clip_05 | `Clip_05_贺平生答五行灵根.mp4` | 4.087s | 720x1280 | yes | 3 |  |

## Seam machine check（尾帧接力 · 前镜 end 帧 vs 后镜 start 帧）

- checked: 2 · block: 0 · warn: 0

| Seam | dHash | Color dist | Verdict |
|---|---:|---:|---|
| Clip_04 → Clip_05 | 33 | 0.0321 | info |
| Clip_05 → Clip_06 | 29 | 0.0268 | info |

## Intra-clip identity sampling（近景片内身份漂移 · start/mid/end 抽帧）

- closeup clips checked: 1 · block: 0 · warn: 1（warn=粗筛交人判；block=近景非双帧镜结构远超重画阈值 dHash>44，拒绝验收；精确同人判定走 n2d-review/temporal_consistency.analyze）

| Clip | Source MP4 | Lens | Max dHash | Verdict |
|---|---|---|---:|---|
| Clip_05 | `Clip_05_贺平生答五行灵根.mp4` | 近景·轻抬眼 | 32 | warn |

## Anchor adherence（中段锚帧消费对账 · storyboard anchor vs generated sample）

- checked: 1 · block: 1 · warn: 0 · skipped: 0

| Clip | Anchor | Sample | Δs | dHash | Color dist | Verdict |
|---|---|---|---:|---:|---:|---|
| Clip_05 | `出图/第1集/图片/Clip05_mid.png` | mid@2.043 | 0.543 | 32 | 0.0141 | block |

Status: pending human review unless the batch manifest marks it accepted.
