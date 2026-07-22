# n2d Video QC

- episode: 第1集
- batch: 01_08
- clips: 8
- contact_sheet: `/Users/wesley/learn/anime-armory/创作区/制漫剧/那妖魔是姜大人/生产数据/video_qc/第1集/01_08/contact_sheet_01_08.jpg`

| Clip | Source MP4 | Duration | Size | FPS | Audio | Frames | Notes |
|---|---|---:|---|---:|---|---:|---|
| Clip_01_part1 | `Clip_01_刀口为何对准人_part1.mp4` | 4.017s | 720x1280 | 24.149 | no | 3 |  |
| Clip_01_part2 | `Clip_01_刀口为何对准人_part2.mp4` | 4.017s | 720x1280 | 24.149 | no | 3 |  |
| Clip_02_part1 | `Clip_02_一炷香前的荒野死局_part1.mp4` | 6.017s | 720x1280 | 24.1 | no | 3 |  |
| Clip_02_part2 | `Clip_02_一炷香前的荒野死局_part2.mp4` | 6.017s | 720x1280 | 24.1 | no | 3 |  |
| Clip_02_part3 | `Clip_02_一炷香前的荒野死局_part3.mp4` | 4.016s | 720x1280 | 24.149 | no | 3 |  |
| Clip_03_part1 | `Clip_03_以脱籍换搀扶_part1.mp4` | 6.017s | 720x1280 | 24.1 | no | 3 |  |
| Clip_03_part2 | `Clip_03_以脱籍换搀扶_part2.mp4` | 4.017s | 720x1280 | 24.149 | no | 3 |  |
| Clip_03_part3 | `Clip_03_以脱籍换搀扶_part3.mp4` | 4.017s | 720x1280 | 24.149 | no | 3 |  |

## Seam machine check（按 seam_mode 分类；仅 relay 同帧阻断）

- checked: 2 · block: 0 · warn: 1

| Seam | dHash | Color dist | Verdict |
|---|---:|---:|---|
| Clip_01 → Clip_02 | 34 | 0.1615 | warn |
| Clip_02 → Clip_03 | 30 | 0.04 | info |

Status: pending human review unless the batch manifest marks it accepted.
