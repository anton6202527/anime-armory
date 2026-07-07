# 中段锚帧规划 — 第1集

- **视频后端消费计划**：backend=未固定；channel=未固定；execution=unknown；mode=unknown_manual_confirm；action=manual confirmation required before paid generation
- 命中 Clip：5 个；新增锚帧 5 张
- **成本增量**：多出图 **5 张**（便宜）。视频成本看执行后端：**multiframe2video（即梦，首选）= 仍 1 次调用/Clip，不翻倍**；仅 frames2video-only 后端才退化为 K+1 段（共 3 段）。
- 确认后用 `--write` 注回 storyboard.json，再走 n2d-image 出 `_aK`/`_mid` 锚帧

## EP01_CLIP01（19.573s）— D0 三帧契约默认中锚（use=split）
- 锚点：9.79s→Clip_01_mid.png

## EP01_CLIP02（9.76s）— D0 三帧契约默认中锚（use=split）
- 锚点：4.88s→Clip_02_mid.png

## EP01_CLIP03（3.003s）— D0 三帧契约默认中锚（use=qc）
- 锚点：1.5s→Clip_03_mid.png

## EP01_CLIP05（7.099s）— D0 三帧契约默认中锚（use=qc）
- 锚点：3.55s→Clip_05_mid.png

## EP01_CLIP06（16.572s）— D0 三帧契约默认中锚（use=split）
- 锚点：8.29s→Clip_06_mid.png

## 三帧契约豁免（极短镜）
- EP01_CLIP04（2.96s）：极短镜 <3.0s，中帧与首尾几乎重合（三帧契约豁免）

## 跳过
- EP01_CLIP01：已有 midframe/anchors 但时间越界或不可解析，按当前 duration 重算
- EP01_CLIP02：已有 midframe/anchors 但时间越界或不可解析，按当前 duration 重算
- EP01_CLIP03：已有 midframe/anchors 但时间越界或不可解析，按当前 duration 重算
- EP01_CLIP04：已有 midframe/anchors 但时间越界或不可解析，按当前 duration 重算
- EP01_CLIP05：已有 midframe/anchors 但时间越界或不可解析，按当前 duration 重算
- EP01_CLIP06：已有 midframe/anchors 但时间越界或不可解析，按当前 duration 重算
