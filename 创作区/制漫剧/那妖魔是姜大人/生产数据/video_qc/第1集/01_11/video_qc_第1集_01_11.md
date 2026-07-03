# n2d Video QC

- episode: 第1集
- batch: 01_11
- clips: 16
- contact_sheet: `/Users/lalala/learn/anime-armory/创作区/制漫剧/那妖魔是姜大人/生产数据/video_qc/第1集/01_11/contact_sheet_01_11.jpg`

| Clip | Source MP4 | Duration | Size | Audio | Frames | Notes |
|---|---|---:|---|---|---:|---|
| Clip_01 | `Clip_01_死人堆惊醒.mp4` | 10.054s | 720x1280 | yes | 3 |  |
| Clip_02_part1 | `Clip_02_看见虎妖尸身_part1.mp4` | 4.063s | 720x1280 | yes | 3 |  |
| Clip_02_part2 | `Clip_02_看见虎妖尸身_part2.mp4` | 13.096s | 720x1280 | yes | 3 |  |
| Clip_03_part1 | `Clip_03_镇魔司压迫交易_part1.mp4` | 4.063s | 720x1280 | yes | 3 |  |
| Clip_03_part2 | `Clip_03_镇魔司压迫交易_part2.mp4` | 15.093s | 720x1280 | yes | 3 |  |
| Clip_04 | `Clip_04_被迫扶裴南行.mp4` | 10.183s | 704x1248 | no | 3 |  |
| Clip_05_part1 | `Clip_05_虎妖诈死复苏_part1.mp4` | 4.087s | 720x1280 | yes | 3 |  |
| Clip_05_part2 | `Clip_05_虎妖诈死复苏_part2.mp4` | 9.102s | 720x1280 | yes | 3 |  |
| Clip_06_part1 | `Clip_06_裴长青最后一击被踹飞_part1.mp4` | 4.087s | 720x1280 | yes | 3 |  |
| Clip_06_part2 | `Clip_06_裴长青最后一击被踹飞_part2.mp4` | 12.098s | 720x1280 | yes | 3 |  |
| Clip_07_part1 | `Clip_07_百妖谱第一次开启_part1.mp4` | 4.087s | 720x1280 | yes | 3 |  |
| Clip_07_part2 | `Clip_07_百妖谱第一次开启_part2.mp4` | 9.102s | 720x1280 | yes | 3 |  |
| Clip_08 | `Clip_08_系统规则指向唯一活物.mp4` | 8.683s | 704x1248 | no | 3 |  |
| Clip_09 | `Clip_09_刀尖抬起.mp4` | 10.183s | 704x1248 | no | 3 |  |
| Clip_10 | `Clip_10_刺杀裴长青.mp4` | 6.683s | 704x1248 | no | 3 |  |
| Clip_11 | `Clip_11_我只想活下去.mp4` | 4.063s | 720x1280 | yes | 3 |  |

## Seam machine check（尾帧接力 · 前镜 end 帧 vs 后镜 start 帧）

- checked: 10 · block: 0 · warn: 0

| Seam | dHash | Color dist | Verdict |
|---|---:|---:|---|
| Clip_01 → Clip_02 | 29 | 0.0276 | info |
| Clip_02 → Clip_03 | 34 | 0.035 | info |
| Clip_03 → Clip_04 | 43 | 0.1694 | info |
| Clip_04 → Clip_05 | 30 | 0.2502 | info |
| Clip_05 → Clip_06 | 31 | 0.0968 | info |
| Clip_06 → Clip_07 | 35 | 0.0428 | info |
| Clip_07 → Clip_08 | 27 | 0.258 | info |
| Clip_08 → Clip_09 | 25 | 0.0909 | info |
| Clip_09 → Clip_10 | 27 | 0.1033 | info |
| Clip_10 → Clip_11 | 36 | 0.0204 | info |

## Intra-clip identity sampling（近景片内身份漂移 · start/mid/end 抽帧）

- closeup clips checked: 15 · block: 0 · warn: 7（warn=粗筛交人判；block=近景非双帧镜结构远超重画阈值 dHash>44，拒绝验收；精确同人判定走 n2d-review/temporal_consistency.analyze）

| Clip | Source MP4 | Lens | Max dHash | Verdict |
|---|---|---|---:|---|
| Clip_01 | `Clip_01_死人堆惊醒.mp4` | ECU 固定；ELS→LS 缓慢推近 | 38 | warn |
| Clip_05_part1 | `Clip_05_虎妖诈死复苏_part1.mp4` | CU 硬切；LS 低机位慢推 | 33 | warn |
| Clip_05_part2 | `Clip_05_虎妖诈死复苏_part2.mp4` | CU 硬切；LS 低机位慢推 | 38 | warn |
| Clip_06_part1 | `Clip_06_裴长青最后一击被踹飞_part1.mp4` | MS 固定微推；CU 命中帧；MS 低机位 | 34 | warn |
| Clip_06_part2 | `Clip_06_裴长青最后一击被踹飞_part2.mp4` | MS 固定微推；CU 命中帧；MS 低机位 | 30 | warn |
| Clip_07_part2 | `Clip_07_百妖谱第一次开启_part2.mp4` | CU；POV 慢推 | 31 | warn |
| Clip_11 | `Clip_11_我只想活下去.mp4` | CU 缓慢推近 | 33 | warn |

## Anchor adherence（中段锚帧消费对账 · storyboard anchor vs generated sample）

- checked: 5 · block: 1 · warn: 1 · skipped: 0

| Clip | Anchor | Sample | Δs | dHash | Color dist | Verdict |
|---|---|---|---:|---:|---:|---|
| Clip_01 | `出图/第1集/图片/Clip01_mid.png` | mid@5.027 | 2.027 | 37 | 0.0764 | block |
| Clip_04 | `出图/第1集/图片/Clip04_mid.png` | mid@5.092 | 1.092 | 19 | 0.008 | warn |

Status: pending human review unless the batch manifest marks it accepted.
