# n2d Video QC

- episode: 第2集
- batch: 05_08
- clips: 7
- contact_sheet: `/Users/wesley/learn/anime-armory/创作区/制漫剧/那妖魔是姜大人/生产数据/video_qc/第2集/05_08/contact_sheet_05_08.jpg`

| Clip | Source MP4 | Duration | Size | FPS | Audio | Frames | Notes |
|---|---|---:|---|---:|---|---:|---|
| Clip_05_part1 | `Clip_05_摹影虎山神获圆满刀法_part1.mp4` | 4.017s | 1080x1920 | 24.149 | no | 3 |  |
| Clip_05_part2 | `Clip_05_摹影虎山神获圆满刀法_part2.mp4` | 7.017s | 720x1280 | 24.086 | no | 3 |  |
| Clip_06 | `Clip_06_结算闻弦初境与二十五年余额.mp4` | 11.017s | 720x1280 | 24.054 | no | 3 |  |
| Clip_07_part1 | `Clip_07_替裴合眼与还命承诺_part1.mp4` | 4.016s | 720x1280 | 24.149 | no | 3 |  |
| Clip_07_part2 | `Clip_07_替裴合眼与还命承诺_part2.mp4` | 8.016s | 720x1280 | 24.075 | no | 3 |  |
| Clip_08_part1 | `Clip_08_摹影进阶会变成什么_part1.mp4` | 4.017s | 720x1280 | 24.149 | no | 3 |  |
| Clip_08_part2 | `Clip_08_摹影进阶会变成什么_part2.mp4` | 4.017s | 720x1280 | 24.149 | no | 3 |  |

## Seam machine check（按 seam_mode 分类；仅 relay 同帧阻断）

- checked: 4 · block: 0 · warn: 0
- note: 交付一致性 warn：Clip_05_part1 resolution=1080x1920（批内众数 720x1280）——混帧率/混分辨率进 compose 会被静默规格化掩盖，先确认该 clip 是否该重出。

| Seam | dHash | Color dist | Verdict |
|---|---:|---:|---|
| Clip_05 → Clip_06 | 30 | 0.1166 | info |
| Clip_06 → Clip_07 | 29 | 0.0362 | info |
| Clip_07 → Clip_08 | 32 | 0.0081 | info |

## Intra-clip identity sampling（近景片内身份漂移 · start/mid/end 抽帧）

- closeup clips checked: 7 · block: 0 · warn: 2（warn=粗筛交人判；block=近景非双帧镜结构远超重画阈值 dHash>44，拒绝验收；精确同人判定走 n2d-review/temporal_consistency.analyze）

| Clip | Source MP4 | Lens | Max dHash | Verdict |
|---|---|---|---:|---|
| Clip_06 | `Clip_06_结算闻弦初境与二十五年余额.mp4` | MCU固定；CU轻拉 | 35 | warn |
| Clip_07_part1 | `Clip_07_替裴合眼与还命承诺_part1.mp4` | MS轻跟；CU固定 | 35 | warn |

## Anchor adherence（中段锚帧消费对账 · storyboard anchor vs generated sample）

- checked: 1 · block: 0 · warn: 0 · skipped: 0

Status: pending human review unless the batch manifest marks it accepted.
