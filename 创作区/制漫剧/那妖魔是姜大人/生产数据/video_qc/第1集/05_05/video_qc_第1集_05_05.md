# n2d Video QC

- episode: 第1集
- batch: 05_05
- clips: 1
- contact_sheet: `创作区/制漫剧/那妖魔是姜大人/生产数据/video_qc/第1集/05_05/contact_sheet_05_05.jpg`

| Clip | Source MP4 | Duration | Size | Audio | Frames | Notes |
|---|---|---:|---|---|---:|---|
| Clip_05_part2 | `Clip_05_虎妖诈死复苏_part2.mp4` | 9.102s | 720x1280 | yes | 3 |  |

## Seam machine check（尾帧接力 · 前镜 end 帧 vs 后镜 start 帧）

- checked: 2 · block: 0 · warn: 0

| Seam | dHash | Color dist | Verdict |
|---|---:|---:|---|
| Clip_04 → Clip_05 | 30 | 0.2502 | info |
| Clip_05 → Clip_06 | 41 | 0.1285 | info |

## Intra-clip identity sampling（近景片内身份漂移 · start/mid/end 抽帧）

- closeup clips checked: 1 · block: 0 · warn: 1（warn=粗筛交人判；block=近景非双帧镜结构远超重画阈值 dHash>44，拒绝验收；精确同人判定走 n2d-review/temporal_consistency.analyze）

| Clip | Source MP4 | Lens | Max dHash | Verdict |
|---|---|---|---:|---|
| Clip_05_part2 | `Clip_05_虎妖诈死复苏_part2.mp4` | CU 硬切；LS 低机位慢推 | 38 | warn |

Status: pending human review unless the batch manifest marks it accepted.
