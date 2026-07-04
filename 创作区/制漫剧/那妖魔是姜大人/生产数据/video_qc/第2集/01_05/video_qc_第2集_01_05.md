# n2d Video QC

- episode: 第2集
- batch: 01_05
- clips: 5
- contact_sheet: `/Users/lalala/learn/anime-armory/创作区/制漫剧/那妖魔是姜大人/生产数据/video_qc/第2集/01_05/contact_sheet_01_05.jpg`

| Clip | Source MP4 | Duration | Size | Audio | Frames | Notes |
|---|---|---:|---|---|---:|---|
| Clip_01 | `Clip_01_杀裴后的二十年到账.mp4` | 13.183s | 704x1248 | no | 3 |  |
| Clip_02 | `Clip_02_虎妖嘲讽与转刀.mp4` | 12.183s | 704x1248 | no | 3 |  |
| Clip_03 | `Clip_03_二十年尽压一刀.mp4` | 11.683s | 704x1248 | no | 3 |  |
| Clip_04 | `Clip_04_一刀斩虎山神.mp4` | 12.183s | 704x1248 | no | 3 |  |
| Clip_05 | `Clip_05_一百年到账与收录选择.mp4` | 9.183s | 704x1248 | no | 3 |  |

## Seam machine check（尾帧接力 · 前镜 end 帧 vs 后镜 start 帧）

- checked: 4 · block: 0 · warn: 0
- note: 部分中段锚帧离 start/mid/end 三采样点太远或 PNG 缺失，锚帧消费对账跳过；必要时加密抽帧复核。

| Seam | dHash | Color dist | Verdict |
|---|---:|---:|---|
| Clip_01 → Clip_02 | 30 | 0.2297 | info |
| Clip_02 → Clip_03 | 32 | 0.1343 | info |
| Clip_03 → Clip_04 | 19 | 0.1005 | info |
| Clip_04 → Clip_05 | 23 | 0.0684 | info |

## Intra-clip identity sampling（近景片内身份漂移 · start/mid/end 抽帧）

- closeup clips checked: 4 · block: 0 · warn: 0（warn=粗筛交人判；block=近景非双帧镜结构远超重画阈值 dHash>44，拒绝验收；精确同人判定走 n2d-review/temporal_consistency.analyze）

## Anchor adherence（中段锚帧消费对账 · storyboard anchor vs generated sample）

- checked: 7 · block: 0 · warn: 3 · skipped: 1

| Clip | Anchor | Sample | Δs | dHash | Color dist | Verdict |
|---|---|---|---:|---:|---:|---|
| Clip_03 | `出图/第2集/图片/Clip03_a1.png` | mid@5.842 | 1.642 | 20 | 0.1289 | warn |
| Clip_04 | `出图/第2集/图片/Clip04_a1.png` | mid@6.092 | 2.292 | 25 | 0.0335 | warn |
| Clip_04 | `出图/第2集/图片/Clip04_a3.png` | end@11.983 | 1.583 | 20 | 0.0277 | warn |

Status: pending human review unless the batch manifest marks it accepted.
