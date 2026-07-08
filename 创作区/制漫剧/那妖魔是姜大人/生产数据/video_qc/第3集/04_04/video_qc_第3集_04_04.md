# n2d Video QC

- episode: 第3集
- batch: 04_04
- clips: 1
- contact_sheet: `/Users/wesley/learn/anime-armory/创作区/制漫剧/那妖魔是姜大人/生产数据/video_qc/第3集/04_04/contact_sheet_04_04.jpg`

| Clip | Source MP4 | Duration | Size | Audio | Frames | Notes |
|---|---|---:|---|---|---:|---|
| Clip_04 | `Clip_04_掌心刀法与身份死局.mp4` | 35.183s | 704x1248 | no | 3 |  |

## Seam machine check（尾帧接力 · 前镜 end 帧 vs 后镜 start 帧）

- checked: 1 · block: 0 · warn: 0
- note: 部分中段锚帧离 start/mid/end 三采样点太远或 PNG 缺失，锚帧消费对账跳过；必要时加密抽帧复核。

| Seam | dHash | Color dist | Verdict |
|---|---:|---:|---|
| Clip_03 → Clip_04 | 20 | 0.0864 | info |

## Intra-clip identity sampling（近景片内身份漂移 · start/mid/end 抽帧）

- closeup clips checked: 1 · block: 0 · warn: 0（warn=粗筛交人判；block=近景非双帧镜结构远超重画阈值 dHash>44，拒绝验收；精确同人判定走 n2d-review/temporal_consistency.analyze）

## Anchor adherence（中段锚帧消费对账 · storyboard anchor vs generated sample）

- checked: 5 · block: 0 · warn: 2 · skipped: 1

| Clip | Anchor | Sample | Δs | dHash | Color dist | Verdict |
|---|---|---|---:|---:|---:|---|
| Clip_04 | `出图/第3集/图片/Clip04_first_a4.png` | mid@17.592 | 1.468 | 19 | 0.0047 | warn |
| Clip_04 | `出图/第3集/图片/Clip04_first_a5.png` | mid@17.592 | 6.238 | 21 | 0.0063 | warn |

Status: pending human review unless the batch manifest marks it accepted.
