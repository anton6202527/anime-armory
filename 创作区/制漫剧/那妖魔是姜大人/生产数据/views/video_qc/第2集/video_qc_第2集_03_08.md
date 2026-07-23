# n2d Video QC

- episode: 第2集
- batch: 03_08
- clips: 4
- contact_sheet: `/Users/wesley/learn/anime-armory/创作区/制漫剧/那妖魔是姜大人/生产数据/video_qc/第2集/03_08/contact_sheet_03_08.jpg`

| Clip | Source MP4 | Duration | Size | FPS | Audio | Frames | Notes |
|---|---|---:|---|---:|---|---:|---|
| Clip_03_part1 | `Clip_03_一刀断虎首_part1.mp4` | 4.042s | 1080x1920 | 24 | no | 3 |  |
| Clip_03_part2 | `Clip_03_一刀断虎首_part2.mp4` | 4.042s | 1080x1920 | 24 | no | 3 |  |
| Clip_03_part3 | `Clip_03_一刀断虎首_part3.mp4` | 6.042s | 1080x1920 | 24 | no | 3 |  |
| Clip_04 | `Clip_04_百年道行与收录选择.mp4` | 6.017s | 1080x1920 | 24.1 | no | 3 |  |

## Seam machine check（按 seam_mode 分类；仅 relay 同帧阻断）

- checked: 2 · block: 1 · warn: 1

| Seam | dHash | Color dist | Verdict |
|---|---:|---:|---|
| Clip_02 → Clip_03 | 34 | 0.1006 | block |
| Clip_03 → Clip_04 | 22 | 0.1584 | warn |

## Intra-clip identity sampling（近景片内身份漂移 · start/mid/end 抽帧）

- closeup clips checked: 4 · block: 0 · warn: 1（warn=粗筛交人判；block=近景非双帧镜结构远超重画阈值 dHash>44，拒绝验收；精确同人判定走 n2d-review/temporal_consistency.analyze）

| Clip | Source MP4 | Lens | Max dHash | Verdict |
|---|---|---|---:|---|
| Clip_03_part1 | `Clip_03_一刀断虎首_part1.mp4` | CU固定+轻冲击；MS固定；CU结果镜 | 33 | warn |

Status: pending human review unless the batch manifest marks it accepted.
