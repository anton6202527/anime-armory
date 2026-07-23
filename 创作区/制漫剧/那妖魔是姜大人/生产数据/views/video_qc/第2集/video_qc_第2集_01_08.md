# n2d Video QC

- episode: 第2集
- batch: 01_08
- clips: 3
- contact_sheet: `/Users/wesley/learn/anime-armory/创作区/制漫剧/那妖魔是姜大人/生产数据/video_qc/第2集/01_08/contact_sheet_01_08.jpg`

| Clip | Source MP4 | Duration | Size | FPS | Audio | Frames | Notes |
|---|---|---:|---|---:|---|---:|---|
| Clip_01_part1 | `Clip_01_杀人余震与二十年到账_part1.mp4` | 4.017s | 1080x1920 | 24.149 | no | 3 |  |
| Clip_01_part2 | `Clip_01_杀人余震与二十年到账_part2.mp4` | 5.017s | 1080x1920 | 24.12 | no | 3 |  |
| Clip_01_part3 | `Clip_01_杀人余震与二十年到账_part3.mp4` | 5.017s | 1080x1920 | 24.12 | no | 3 |  |

## Seam machine check（按 seam_mode 分类；仅 relay 同帧阻断）

- checked: 0 · block: 0 · warn: 0

## Intra-clip identity sampling（近景片内身份漂移 · start/mid/end 抽帧）

- closeup clips checked: 3 · block: 0 · warn: 0（warn=粗筛交人判；block=近景非双帧镜结构远超重画阈值 dHash>44，拒绝验收；精确同人判定走 n2d-review/temporal_consistency.analyze）

Status: pending human review unless the batch manifest marks it accepted.
