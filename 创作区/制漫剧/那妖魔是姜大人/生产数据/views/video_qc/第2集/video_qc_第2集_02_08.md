# n2d Video QC

- episode: 第2集
- batch: 02_08
- clips: 2
- contact_sheet: `/Users/wesley/learn/anime-armory/创作区/制漫剧/那妖魔是姜大人/生产数据/video_qc/第2集/02_08/contact_sheet_02_08.jpg`

| Clip | Source MP4 | Duration | Size | FPS | Audio | Frames | Notes |
|---|---|---:|---|---:|---|---:|---|
| Clip_02_part1 | `Clip_02_二十年尽付一刀_part1.mp4` | 7.017s | 1080x1920 | 24.086 | no | 3 |  |
| Clip_02_part2 | `Clip_02_二十年尽付一刀_part2.mp4` | 7.017s | 1080x1920 | 24.086 | no | 3 |  |

## Seam machine check（按 seam_mode 分类；仅 relay 同帧阻断）

- checked: 1 · block: 0 · warn: 0

| Seam | dHash | Color dist | Verdict |
|---|---:|---:|---|
| Clip_01 → Clip_02 | 23 | 0.0496 | info |

## Intra-clip identity sampling（近景片内身份漂移 · start/mid/end 抽帧）

- closeup clips checked: 2 · block: 0 · warn: 0（warn=粗筛交人判；block=近景非双帧镜结构远超重画阈值 dHash>44，拒绝验收；精确同人判定走 n2d-review/temporal_consistency.analyze）

Status: pending human review unless the batch manifest marks it accepted.
