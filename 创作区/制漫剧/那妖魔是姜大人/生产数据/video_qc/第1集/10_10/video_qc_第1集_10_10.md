# n2d Video QC

- episode: 第1集
- batch: 10_10
- clips: 1
- contact_sheet: `创作区/制漫剧/那妖魔是姜大人/生产数据/video_qc/第1集/10_10/contact_sheet_10_10.jpg`

| Clip | Source MP4 | Duration | Size | Audio | Frames | Notes |
|---|---|---:|---|---|---:|---|
| Clip_10 | `Clip_10_刺杀裴长青.mp4` | 6.683s | 704x1248 | no | 3 |  |

## Seam machine check（尾帧接力 · 前镜 end 帧 vs 后镜 start 帧）

- checked: 2 · block: 0 · warn: 0

| Seam | dHash | Color dist | Verdict |
|---|---:|---:|---|
| Clip_09 → Clip_10 | 27 | 0.1033 | info |
| Clip_10 → Clip_11 | 36 | 0.0204 | info |

## Intra-clip identity sampling（近景片内身份漂移 · start/mid/end 抽帧）

- closeup clips checked: 1 · block: 0 · warn: 0（warn=粗筛交人判；block=近景非双帧镜结构远超重画阈值 dHash>44，拒绝验收；精确同人判定走 n2d-review/temporal_consistency.analyze）

## Anchor adherence（中段锚帧消费对账 · storyboard anchor vs generated sample）

- checked: 1 · block: 0 · warn: 0 · skipped: 0

Status: pending human review unless the batch manifest marks it accepted.
