# n2d Video QC

- episode: 第1集
- batch: 05_05
- clips: 1
- contact_sheet: `/Users/wesley/learn/anime-armory/创作区/制漫剧/那妖魔是姜大人/生产数据/video_qc/第1集/05_05/contact_sheet_05_05.jpg`

| Clip | Source MP4 | Duration | Size | FPS | Audio | Frames | Notes |
|---|---|---:|---|---:|---|---:|---|
| Clip_05_part3 | `Clip_05_死妖咳嗽站起_part3.mp4` | 4.017s | 720x1280 | 24.149 | no | 3 |  |

## Seam machine check（按 seam_mode 分类；仅 relay 同帧阻断）

- checked: 1 · block: 0 · warn: 0
- note: storyboard 景别不可用——片内身份采样对全部 clip 抽样（可能含非近景）。

| Seam | dHash | Color dist | Verdict |
|---|---:|---:|---|
| Clip_04 → Clip_05 | 35 | 0.1165 | info |

## Intra-clip identity sampling（近景片内身份漂移 · start/mid/end 抽帧）

- closeup clips checked: 1 · block: 0 · warn: 0（warn=粗筛交人判；block=近景非双帧镜结构远超重画阈值 dHash>44，拒绝验收；精确同人判定走 n2d-review/temporal_consistency.analyze）

Status: pending human review unless the batch manifest marks it accepted.
