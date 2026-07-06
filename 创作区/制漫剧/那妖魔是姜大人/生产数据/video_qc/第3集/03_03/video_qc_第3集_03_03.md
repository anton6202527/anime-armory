# n2d Video QC

- episode: 第3集
- batch: 03_03
- clips: 1
- contact_sheet: `/Users/wesley/learn/anime-armory/创作区/制漫剧/那妖魔是姜大人/生产数据/video_qc/第3集/03_03/contact_sheet_03_03.jpg`

| Clip | Source MP4 | Duration | Size | Audio | Frames | Notes |
|---|---|---:|---|---|---:|---|
| Clip_03 | `Clip_03_黑衣赤纹：借来的官威.mp4` | 25.183s | 704x1248 | no | 3 |  |

## Seam machine check（尾帧接力 · 前镜 end 帧 vs 后镜 start 帧）

- checked: 1 · block: 0 · warn: 0

| Seam | dHash | Color dist | Verdict |
|---|---:|---:|---|
| Clip_02 → Clip_03 | 19 | 0.0179 | info |

## Intra-clip identity sampling（近景片内身份漂移 · start/mid/end 抽帧）

- closeup clips checked: 1 · block: 0 · warn: 1（warn=粗筛交人判；block=近景非双帧镜结构远超重画阈值 dHash>44，拒绝验收；精确同人判定走 n2d-review/temporal_consistency.analyze）

| Clip | Source MP4 | Lens | Max dHash | Verdict |
|---|---|---|---:|---|
| Clip_03 | `Clip_03_黑衣赤纹：借来的官威.mp4` | CU 衣纹；MS 完成态；CU 腰刀/眼神 | 33 | warn |

## Anchor adherence（中段锚帧消费对账 · storyboard anchor vs generated sample）

- checked: 4 · block: 0 · warn: 3 · skipped: 0

| Clip | Anchor | Sample | Δs | dHash | Color dist | Verdict |
|---|---|---|---:|---:|---:|---|
| Clip_03 | `出图/第3集/图片/Clip03_first_a2.png` | mid@12.592 | 2.782 | 28 | 0.0188 | warn |
| Clip_03 | `出图/第3集/图片/Clip03_first_a3.png` | mid@12.592 | 2.128 | 27 | 0.0164 | warn |
| Clip_03 | `出图/第3集/图片/Clip03_first_a4.png` | end@24.983 | 5.363 | 17 | 0.1471 | warn |

Status: pending human review unless the batch manifest marks it accepted.
