# n2d Video QC

- episode: 第3集
- batch: 01_08
- clips: 7
- contact_sheet: `/Users/wesley/learn/anime-armory/创作区/制漫剧/那妖魔是姜大人/生产数据/video_qc/第3集/01_08/contact_sheet_01_08.jpg`

| Clip | Source MP4 | Duration | Size | FPS | Audio | Frames | Notes |
|---|---|---:|---|---:|---|---:|---|
| Clip_01_part1 | `Clip_01_众人跪求的假大人_part1.mp4` | 6.017s | 1080x1920 | 24.1 | no | 3 |  |
| Clip_01_part2 | `Clip_01_众人跪求的假大人_part2.mp4` | 6.017s | 1080x1920 | 24.1 | no | 3 |  |
| Clip_02 | `Clip_02_荒坡埋尸告别.mp4` | 8.016s | 1080x1920 | 24.075 | no | 3 |  |
| Clip_03 | `Clip_03_黑衣赤纹换装.mp4` | 12.017s | 1080x1920 | 24.05 | no | 3 |  |
| Clip_04_part1 | `Clip_04_贱籍死局与马蹄_part1.mp4` | 8.017s | 1080x1920 | 24.075 | no | 3 |  |
| Clip_04_part2 | `Clip_04_贱籍死局与马蹄_part2.mp4` | 8.017s | 720x1280 | 24.075 | no | 3 |  |
| Clip_05_part1 | `Clip_05_马队急停试探_part1.mp4` | 4.017s | 720x1280 | 24.149 | no | 3 |  |

## Seam machine check（按 seam_mode 分类；仅 relay 同帧阻断）

- checked: 4 · block: 0 · warn: 2
- note: 部分中段锚帧离 start/mid/end 三采样点太远或 PNG 缺失，锚帧消费对账跳过；必要时加密抽帧复核。
- note: 交付一致性 warn：Clip_04_part2 resolution=720x1280（批内众数 1080x1920）——混帧率/混分辨率进 compose 会被静默规格化掩盖，先确认该 clip 是否该重出。
- note: 交付一致性 warn：Clip_05_part1 resolution=720x1280（批内众数 1080x1920）——混帧率/混分辨率进 compose 会被静默规格化掩盖，先确认该 clip 是否该重出。

| Seam | dHash | Color dist | Verdict |
|---|---:|---:|---|
| Clip_01 → Clip_02 | 27 | 0.2249 | info |
| Clip_02 → Clip_03 | 33 | 0.435 | warn |
| Clip_03 → Clip_04 | 32 | 0.1126 | info |
| Clip_04 → Clip_05 | 19 | 0.1403 | warn |

## Anchor adherence（中段锚帧消费对账 · storyboard anchor vs generated sample）

- checked: 0 · block: 0 · warn: 0 · skipped: 1

Status: pending human review unless the batch manifest marks it accepted.
