# n2d Video QC

- episode: 第1集
- batch: 02_02
- clips: 1
- contact_sheet: `/Users/wesley/learn/anime-armory/创作区/制漫剧/那妖魔是姜大人/生产数据/video_qc/第1集/02_02/contact_sheet_02_02.jpg`

| Clip | Source MP4 | Duration | Size | FPS | Audio | Frames | Notes |
|---|---|---:|---|---:|---|---:|---|
| Clip_02_part1 | `Clip_02_一炷香前的荒野死局_part1.mp4` | 5.792s | 720x1280 | 24 | no | 3 |  |

## Seam machine check（按 seam_mode 分类；仅 relay 同帧阻断）

- checked: 2 · block: 0 · warn: 1
- note: storyboard 景别不可用——片内身份采样对全部 clip 抽样（可能含非近景）。

| Seam | dHash | Color dist | Verdict |
|---|---:|---:|---|
| Clip_01 → Clip_02 | 27 | 0.2761 | warn |
| Clip_02 → Clip_03 | 23 | 0.0312 | info |

## Intra-clip identity sampling（近景片内身份漂移 · start/mid/end 抽帧）

- closeup clips checked: 1 · block: 0 · warn: 1（warn=粗筛交人判；block=近景非双帧镜结构远超重画阈值 dHash>44，拒绝验收；精确同人判定走 n2d-review/temporal_consistency.analyze）

| Clip | Source MP4 | Lens | Max dHash | Verdict |
|---|---|---|---:|---|
| Clip_02_part1 | `Clip_02_一炷香前的荒野死局_part1.mp4` | - | 30 | warn |

Status: pending human review unless the batch manifest marks it accepted.
