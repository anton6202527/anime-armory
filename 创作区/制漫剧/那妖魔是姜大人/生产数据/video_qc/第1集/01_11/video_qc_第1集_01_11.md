# n2d Video QC

- episode: 第1集
- batch: 01_11
- clips: 11
- contact_sheet: `/Users/wesley/learn/anime-armory/创作区/制漫剧/那妖魔是姜大人/生产数据/video_qc/第1集/01_11/contact_sheet_01_11.jpg`

| Clip | Source MP4 | Duration | Size | Audio | Frames | Notes |
|---|---|---:|---|---|---:|---|
| Clip_01 | `Clip_01_死人堆惊醒.mp4` | 6.084s | 720x1280 | yes | 3 |  |
| Clip_02 | `Clip_02_看见虎妖尸身.mp4` | 8.183s | 704x1248 | no | 3 |  |
| Clip_03 | `Clip_03_镇魔司压迫交易.mp4` | 11.099s | 720x1280 | yes | 3 |  |
| Clip_04 | `Clip_04_被迫扶裴南行.mp4` | 8.080s | 720x1280 | yes | 3 |  |
| Clip_05 | `Clip_05_虎妖诈死复苏.mp4` | 9.056s | 720x1280 | yes | 3 |  |
| Clip_06 | `Clip_06_裴长青最后一击被踹飞.mp4` | 9.102s | 720x1280 | yes | 3 |  |
| Clip_07 | `Clip_07_百妖谱第一次开启.mp4` | 8.057s | 720x1280 | yes | 3 |  |
| Clip_08 | `Clip_08_系统规则指向唯一活物.mp4` | 8.080s | 720x1280 | yes | 3 |  |
| Clip_09 | `Clip_09_刀尖抬起.mp4` | 8.080s | 720x1280 | yes | 3 |  |
| Clip_10 | `Clip_10_刺杀裴长青.mp4` | 7.082s | 720x1280 | yes | 3 |  |
| Clip_11 | `Clip_11_我只想活下去.mp4` | 6.183s | 704x1248 | no | 3 |  |

## Seam machine check（尾帧接力 · 前镜 end 帧 vs 后镜 start 帧）

- checked: 10 · block: 0 · warn: 0

| Seam | dHash | Color dist | Verdict |
|---|---:|---:|---|
| Clip_01 → Clip_02 | 28 | 0.0352 | info |
| Clip_02 → Clip_03 | 27 | 0.0287 | info |
| Clip_03 → Clip_04 | 33 | 0.107 | info |
| Clip_04 → Clip_05 | 35 | 0.3702 | info |
| Clip_05 → Clip_06 | 36 | 0.0717 | info |
| Clip_06 → Clip_07 | 32 | 0.1106 | info |
| Clip_07 → Clip_08 | 28 | 0.1493 | info |
| Clip_08 → Clip_09 | 31 | 0.0144 | info |
| Clip_09 → Clip_10 | 27 | 0.0662 | info |
| Clip_10 → Clip_11 | 36 | 0.1008 | info |

## Intra-clip identity sampling（近景片内身份漂移 · start/mid/end 抽帧）

- closeup clips checked: 10 · block: 0 · warn: 2（warn=粗筛交人判；block=近景非双帧镜结构远超重画阈值 dHash>44，拒绝验收；精确同人判定走 n2d-review/temporal_consistency.analyze）

| Clip | Source MP4 | Lens | Max dHash | Verdict |
|---|---|---|---:|---|
| Clip_05 | `Clip_05_虎妖诈死复苏.mp4` | CU 硬切；LS 低机位慢推 | 30 | warn |
| Clip_09 | `Clip_09_刀尖抬起.mp4` | LS 压迫远景；CU 慢推 | 30 | warn |

## Anchor adherence（中段锚帧消费对账 · storyboard anchor vs generated sample）

- checked: 11 · block: 1 · warn: 5 · skipped: 0

| Clip | Anchor | Sample | Δs | dHash | Color dist | Verdict |
|---|---|---|---:|---:|---:|---|
| Clip_01 | `出图/第1集/图片/Clip01_mid.png` | mid@3.042 | 0.042 | 23 | 0.0069 | warn |
| Clip_03 | `出图/第1集/图片/Clip03_mid.png` | mid@5.55 | 1.55 | 19 | 0.0264 | warn |
| Clip_05 | `出图/第1集/图片/Clip05_mid.png` | mid@4.528 | 0.528 | 30 | 0.0154 | block |
| Clip_06 | `出图/第1集/图片/Clip06_mid.png` | mid@4.551 | 1.551 | 22 | 0.0258 | warn |
| Clip_09 | `出图/第1集/图片/Clip09_mid.png` | mid@4.04 | 0.04 | 23 | 0.0331 | warn |
| Clip_10 | `出图/第1集/图片/Clip10_mid.png` | mid@3.541 | 0.041 | 29 | 0.0442 | warn |

Status: pending human review unless the batch manifest marks it accepted.
