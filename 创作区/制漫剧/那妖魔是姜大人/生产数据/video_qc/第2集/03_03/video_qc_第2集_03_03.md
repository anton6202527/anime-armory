# n2d Video QC

- episode: 第2集
- batch: 03_03
- clips: 1
- contact_sheet: `/Users/lalala/learn/anime-armory/创作区/制漫剧/那妖魔是姜大人/生产数据/video_qc/第2集/03_03/contact_sheet_03_03.jpg`

| Clip | Source MP4 | Duration | Size | Audio | Frames | Notes |
|---|---|---:|---|---|---:|---|
| Clip_03 | `Clip_03_二十年尽压一刀.mp4` | 11.683s | 704x1248 | no | 3 |  |

## Seam machine check（尾帧接力 · 前镜 end 帧 vs 后镜 start 帧）

- checked: 2 · block: 0 · warn: 0
- note: 部分中段锚帧离 start/mid/end 三采样点太远或 PNG 缺失，锚帧消费对账跳过；必要时加密抽帧复核。

| Seam | dHash | Color dist | Verdict |
|---|---:|---:|---|
| Clip_02 → Clip_03 | 32 | 0.1343 | info |
| Clip_03 → Clip_04 | 19 | 0.1005 | info |

## Intra-clip identity sampling（近景片内身份漂移 · start/mid/end 抽帧）

- closeup clips checked: 1 · block: 0 · warn: 0（warn=粗筛交人判；block=近景非双帧镜结构远超重画阈值 dHash>44，拒绝验收；精确同人判定走 n2d-review/temporal_consistency.analyze）

## Anchor adherence（中段锚帧消费对账 · storyboard anchor vs generated sample）

- checked: 1 · block: 0 · warn: 1 · skipped: 1

| Clip | Anchor | Sample | Δs | dHash | Color dist | Verdict |
|---|---|---|---:|---:|---:|---|
| Clip_03 | `出图/第2集/图片/Clip03_a1.png` | mid@5.842 | 1.642 | 20 | 0.1289 | warn |

Status: pending human review unless the batch manifest marks it accepted.
