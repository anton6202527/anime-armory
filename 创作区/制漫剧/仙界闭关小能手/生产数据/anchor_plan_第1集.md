# 中段锚帧规划 — 第1集

- **视频后端消费计划**：backend=未固定；channel=未固定；execution=unknown；mode=unknown_manual_confirm；action=manual confirmation required before paid generation
- 命中 Clip：6 个；新增锚帧 12 张
- **成本增量**：多出图 **12 张**（便宜）。视频成本看执行后端：**multiframe2video（即梦，首选）= 仍 1 次调用/Clip，不翻倍**；仅 frames2video-only 后端才退化为 K+1 段（共 10 段）。
- 确认后用 `--write` 注回 storyboard.json，再走 n2d-image 出 `_aK`/`_mid` 锚帧

## EP01_CLIP01（25.459s）— R2 普通长镜（25.459s/4拍）
- 锚点：5.09s→Clip_01_a1.png、10.18s→Clip_01_a2.png、15.28s→Clip_01_a3.png、20.37s→Clip_01_a4.png

## EP01_CLIP02（13.332s）— R2 普通长镜（13.332s/3拍）
- 锚点：4.44s→Clip_02_a1.png、8.89s→Clip_02_a2.png

## EP01_CLIP03（3.662s）— D0 三帧契约默认中锚（use=qc）
- 锚点：1.83s→Clip_03_mid.png

## EP01_CLIP04（5.859s）— D0 三帧契约默认中锚（use=qc）
- 锚点：2.93s→Clip_04_mid.png

## EP01_CLIP05（10.943s）— R2 普通长镜（10.943s/4拍）
- 锚点：5.47s→Clip_05_a1.png

## EP01_CLIP06（18.351s）— R2 普通长镜（18.351s/5拍）
- 锚点：4.59s→Clip_06_a1.png、9.18s→Clip_06_a2.png、13.76s→Clip_06_a3.png

## 跳过
- EP01_CLIP01：已有自动 anchors 但源时长已变或缺 source_duration，按当前 duration 重算
- EP01_CLIP01：已有 midframe/anchors 但时间越界或不可解析，按当前 duration 重算
- EP01_CLIP02：已有自动 anchors 但源时长已变或缺 source_duration，按当前 duration 重算
- EP01_CLIP02：已有 midframe/anchors 但时间越界或不可解析，按当前 duration 重算
- EP01_CLIP03：已有自动 anchors 但源时长已变或缺 source_duration，按当前 duration 重算
- EP01_CLIP03：已有 midframe/anchors 但时间越界或不可解析，按当前 duration 重算
- EP01_CLIP04：已有自动 anchors 但源时长已变或缺 source_duration，按当前 duration 重算
- EP01_CLIP04：已有 midframe/anchors 但时间越界或不可解析，按当前 duration 重算
- EP01_CLIP05：已有自动 anchors 但源时长已变或缺 source_duration，按当前 duration 重算
- EP01_CLIP05：已有 midframe/anchors 但时间越界或不可解析，按当前 duration 重算
- EP01_CLIP06：已有自动 anchors 但源时长已变或缺 source_duration，按当前 duration 重算
- EP01_CLIP06：已有 midframe/anchors 但时间越界或不可解析，按当前 duration 重算
