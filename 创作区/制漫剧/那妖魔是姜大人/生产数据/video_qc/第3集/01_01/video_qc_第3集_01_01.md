# n2d Video QC

- episode: 第3集
- batch: 01_01
- clips: 1
- contact_sheet: `/Users/wesley/learn/anime-armory/创作区/制漫剧/那妖魔是姜大人/生产数据/video_qc/第3集/01_01/contact_sheet_01_01.jpg`

| Clip | Source MP4 | Duration | Size | Audio | Frames | Notes |
|---|---|---:|---|---|---:|---|
| Clip_01 | `Clip_01_埋尸冷开：欠命账落地.mp4` | 10.683s | 704x1248 | no | 3 |  |

## Seam machine check（尾帧接力 · 前镜 end 帧 vs 后镜 start 帧）

- checked: 1 · block: 0 · warn: 0

| Seam | dHash | Color dist | Verdict |
|---|---:|---:|---|
| Clip_01 → Clip_02 | 24 | 0.176 | info |

## Intra-clip identity sampling（近景片内身份漂移 · start/mid/end 抽帧）

- closeup clips checked: 1 · block: 0 · warn: 0（warn=粗筛交人判；block=近景非双帧镜结构远超重画阈值 dHash>44，拒绝验收；精确同人判定走 n2d-review/temporal_consistency.analyze）

## Anchor adherence（中段锚帧消费对账 · storyboard anchor vs generated sample）

- checked: 3 · block: 0 · warn: 0 · skipped: 0

Status: pending human review unless the batch manifest marks it accepted.
