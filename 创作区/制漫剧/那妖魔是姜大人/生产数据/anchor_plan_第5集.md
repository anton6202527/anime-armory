# 中段锚帧规划 — 第5集

- **视频后端消费计划**：backend=未固定；channel=Dreamina；execution=dreamina；mode=native_multiframe；action=submit first/mid/end frames in one native multi-keyframe request
- 命中 Clip：9 个；新增锚帧 35 张
- **成本增量**：多出图 **35 张**（便宜）。视频成本看执行后端：**multiframe2video（即梦，首选）= 仍 1 次调用/Clip，不翻倍**；仅 frames2video-only 后端才退化为 K+1 段（共 35 段）。
- 确认后用 `--write` 注回 storyboard.json，再走 n2d-image 出 `_aK`/`_mid` 锚帧

## EP05_CLIP01（19.247s）— R1 高运动模板 fight_exchange（19.247s/3拍）
- 锚点：4.0s→Clip01_first_a1.png、9.0s→Clip01_first_a2.png、11.55s→Clip01_first_a3.png、14.0s→Clip01_first_a4.png

## EP05_CLIP02（15.408s）— R1 高运动模板 fight_exchange（15.408s/4拍）
- 锚点：5.0s→Clip02_first_a1.png、7.7s→Clip02_first_a2.png、11.56s→Clip02_first_a3.png

## EP05_CLIP03（19.89s）— R1 高运动模板 fight_exchange（19.89s/4拍）
- 锚点：4.0s→Clip03_first_a1.png、6.63s→Clip03_first_a2.png、9.0s→Clip03_first_a3.png、13.0s→Clip03_first_a4.png、16.57s→Clip03_first_a5.png

## EP05_CLIP04（10.479s）— R1 高运动信号（文本/运镜或大表情，10.479s）
- 锚点：4.0s→Clip04_first_a1.png、6.99s→Clip04_first_a2.png

## EP05_CLIP05（11.798s）— R1 高运动模板 fight_exchange（11.798s/3拍）
- 锚点：4.0s→Clip05_first_a1.png、8.0s→Clip05_first_a2.png

## EP05_CLIP06（12.093s）— R1 高运动模板 fight_exchange（12.093s/4拍）
- 锚点：3.0s→Clip06_first_a1.png、7.0s→Clip06_first_a2.png、8.06s→Clip06_first_a3.png

## EP05_CLIP07（26.545s）— R1 高运动信号（文本/运镜或大表情，26.545s）
- 锚点：3.32s→Clip07_first_a1.png、6.64s→Clip07_first_a2.png、10.0s→Clip07_first_a3.png、13.27s→Clip07_first_a4.png、16.0s→Clip07_first_a5.png、19.91s→Clip07_first_a6.png、23.23s→Clip07_first_a7.png

## EP05_CLIP08（15.897s）— R1 高运动信号（文本/运镜或大表情，15.897s）
- 锚点：3.18s→Clip08_first_a1.png、5.0s→Clip08_first_a2.png、9.54s→Clip08_first_a3.png、12.0s→Clip08_first_a4.png

## EP05_CLIP09（21.036s）— R1 高运动信号（文本/运镜或大表情，21.036s）
- 锚点：5.0s→Clip09_first_a1.png、7.01s→Clip09_first_a2.png、11.0s→Clip09_first_a3.png、14.02s→Clip09_first_a4.png、18.0s→Clip09_first_a5.png

## 跳过
- EP05_CLIP01：已有自动 anchors 但源时长已变或缺 source_duration，按当前 duration 重算
- EP05_CLIP01：已有 midframe/anchors 但时间越界或不可解析，按当前 duration 重算
- EP05_CLIP02：已有自动 anchors 但源时长已变或缺 source_duration，按当前 duration 重算
- EP05_CLIP02：已有 midframe/anchors 但时间越界或不可解析，按当前 duration 重算
- EP05_CLIP03：已有自动 anchors 但源时长已变或缺 source_duration，按当前 duration 重算
- EP05_CLIP03：已有 midframe/anchors 但时间越界或不可解析，按当前 duration 重算
- EP05_CLIP04：已有 midframe/anchors 但时间越界或不可解析，按当前 duration 重算
- EP05_CLIP05：已有自动 anchors 但源时长已变或缺 source_duration，按当前 duration 重算
- EP05_CLIP05：已有 midframe/anchors 但时间越界或不可解析，按当前 duration 重算
- EP05_CLIP06：已有自动 anchors 但源时长已变或缺 source_duration，按当前 duration 重算
- EP05_CLIP06：已有 midframe/anchors 但时间越界或不可解析，按当前 duration 重算
- EP05_CLIP07：已有自动 anchors 但源时长已变或缺 source_duration，按当前 duration 重算
- EP05_CLIP07：已有 midframe/anchors 但时间越界或不可解析，按当前 duration 重算
- EP05_CLIP08：已有自动 anchors 但源时长已变或缺 source_duration，按当前 duration 重算
- EP05_CLIP08：已有 midframe/anchors 但时间越界或不可解析，按当前 duration 重算
- EP05_CLIP09：已有自动 anchors 但源时长已变或缺 source_duration，按当前 duration 重算
- EP05_CLIP09：已有 midframe/anchors 但时间越界或不可解析，按当前 duration 重算
