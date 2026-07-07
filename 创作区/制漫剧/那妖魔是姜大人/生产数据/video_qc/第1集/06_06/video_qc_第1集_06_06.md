# n2d Video QC

- episode: 第1集
- batch: 06_06
- clips: 1
- contact_sheet: `/Users/wesley/learn/anime-armory/创作区/制漫剧/那妖魔是姜大人/生产数据/video_qc/第1集/06_06/contact_sheet_06_06.jpg`

| Clip | Source MP4 | Duration | Size | Audio | Frames | Notes |
|---|---|---:|---|---|---:|---|
| Clip_06_part2 | `Clip_06_裴长青最后一击被踹飞_part2.mp4` | 10.017s | 720x1280 | no | 3 |  |

## Seam machine check（尾帧接力 · 前镜 end 帧 vs 后镜 start 帧）

- checked: 2 · block: 0 · warn: 0

| Seam | dHash | Color dist | Verdict |
|---|---:|---:|---|
| Clip_05 → Clip_06 | 32 | 0.1465 | info |
| Clip_06 → Clip_07 | 32 | 0.0419 | info |

## Intra-clip identity sampling（近景片内身份漂移 · start/mid/end 抽帧）

- closeup clips checked: 1 · block: 0 · warn: 1（warn=粗筛交人判；block=近景非双帧镜结构远超重画阈值 dHash>44，拒绝验收；精确同人判定走 n2d-review/temporal_consistency.analyze）

| Clip | Source MP4 | Lens | Max dHash | Verdict |
|---|---|---|---:|---|
| Clip_06_part2 | `Clip_06_裴长青最后一击被踹飞_part2.mp4` | MS 固定微推；CU 命中帧；MS 低机位 + 手部/横刀插入镜 | 34 | warn |

Status: pending human review unless the batch manifest marks it accepted.
