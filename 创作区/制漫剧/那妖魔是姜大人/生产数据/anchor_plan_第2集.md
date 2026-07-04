# 中段锚帧规划 — 第2集

- **视频后端消费计划**：backend=未固定；channel=Dreamina；execution=dreamina；mode=native_multiframe；action=submit first/mid/end frames in one native multi-keyframe request
- 命中 Clip：6 个；新增锚帧 14 张
- **成本增量**：多出图 **14 张**（便宜）。视频成本看执行后端：**multiframe2video（即梦，首选）= 仍 1 次调用/Clip，不翻倍**；仅 frames2video-only 后端才退化为 K+1 段（共 14 段）。
- 确认后用 `--write` 注回 storyboard.json，再走 n2d-image 出 `_aK`/`_mid` 锚帧

## EP02_CLIP01（12.582s）— R2 普通长镜（12.582s/3拍）
- 锚点：4.19s→Clip01_first_a1.png、8.39s→Clip01_first_a2.png

## EP02_CLIP02（12.349s）— R1 高运动信号（文本/运镜或大表情，12.349s）
- 锚点：3.09s→Clip02_first_a1.png、6.17s→Clip02_first_a2.png、9.26s→Clip02_first_a3.png

## EP02_CLIP05（9.451s）— R1 高运动信号（文本/运镜或大表情，9.451s）
- 锚点：3.15s→Clip05_first_a1.png、6.3s→Clip05_first_a2.png

## EP02_CLIP06（11.37s）— R1 高运动信号（文本/运镜或大表情，11.37s）
- 锚点：3.79s→Clip06_first_a1.png、7.58s→Clip06_first_a2.png

## EP02_CLIP07（16.492s）— R1 高运动信号（文本/运镜或大表情，16.492s）
- 锚点：3.3s→Clip07_first_a1.png、6.6s→Clip07_first_a2.png、9.9s→Clip07_first_a3.png、13.19s→Clip07_first_a4.png

## EP02_CLIP08（8.812s）— R2 普通长镜（8.812s/4拍）
- 锚点：4.41s→Clip08_first_a1.png

## 跳过
- EP02_CLIP01：已有单 midframe，但命中 R2 普通长镜（12.582s/3拍），升级为 continuity.anchors[]
- EP02_CLIP02：已有单 midframe，但命中 R1 高运动信号（文本/运镜或大表情，12.349s），升级为 continuity.anchors[]
- EP02_CLIP03：已手动声明 anchors，人工优先
- EP02_CLIP04：已手动声明 anchors，人工优先
- EP02_CLIP05：已有单 midframe，但命中 R1 高运动信号（文本/运镜或大表情，9.451s），升级为 continuity.anchors[]
- EP02_CLIP06：已有单 midframe，但命中 R1 高运动信号（文本/运镜或大表情，11.37s），升级为 continuity.anchors[]
- EP02_CLIP07：已有单 midframe，但命中 R1 高运动信号（文本/运镜或大表情，16.492s），升级为 continuity.anchors[]
- EP02_CLIP08：已有单 midframe，但命中 R2 普通长镜（8.812s/4拍），升级为 continuity.anchors[]
- EP02_CLIP09：已手动声明 anchors，人工优先
- EP02_CLIP10：已手动声明 anchors，人工优先
