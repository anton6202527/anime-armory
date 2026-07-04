# 中段锚帧规划 — 第3集

- **视频后端消费计划**：backend=未固定；channel=Dreamina；execution=dreamina；mode=native_multiframe；action=submit first/mid/end frames in one native multi-keyframe request
- 命中 Clip：8 个；新增锚帧 34 张
- **成本增量**：多出图 **34 张**（便宜）。视频成本看执行后端：**multiframe2video（即梦，首选）= 仍 1 次调用/Clip，不翻倍**；仅 frames2video-only 后端才退化为 K+1 段（共 34 段）。
- 确认后用 `--write` 注回 storyboard.json，再走 n2d-image 出 `_aK`/`_mid` 锚帧

## EP03_CLIP01（12.358s）— R1 高运动信号（文本/运镜或大表情，12.358s）
- 锚点：3.09s→Clip01_first_a1.png、6.18s→Clip01_first_a2.png、9.27s→Clip01_first_a3.png

## EP03_CLIP03（24.531s）— R2 普通长镜（24.531s/3拍）
- 锚点：4.91s→Clip03_first_a1.png、9.81s→Clip03_first_a2.png、14.72s→Clip03_first_a3.png、19.62s→Clip03_first_a4.png

## EP03_CLIP04（33.363s）— R2 普通长镜（33.363s/3拍）
- 锚点：4.77s→Clip04_first_a1.png、9.53s→Clip04_first_a2.png、14.3s→Clip04_first_a3.png、19.06s→Clip04_first_a4.png、23.83s→Clip04_first_a5.png、28.6s→Clip04_first_a6.png

## EP03_CLIP06（20.956s）— R2 普通长镜（20.956s/4拍）
- 锚点：5.24s→Clip06_first_a1.png、10.48s→Clip06_first_a2.png、15.72s→Clip06_first_a3.png

## EP03_CLIP07（13.797s）— R2 普通长镜（13.797s/4拍）
- 锚点：4.6s→Clip07_first_a1.png、9.2s→Clip07_first_a2.png

## EP03_CLIP08（34.092s）— R1 高运动信号（文本/运镜或大表情，34.092s）
- 锚点：3.41s→Clip08_first_a1.png、6.82s→Clip08_first_a2.png、10.23s→Clip08_first_a3.png、13.64s→Clip08_first_a4.png、17.05s→Clip08_first_a5.png、20.46s→Clip08_first_a6.png、23.86s→Clip08_first_a7.png、27.27s→Clip08_first_a8.png、30.68s→Clip08_first_a9.png

## EP03_CLIP09（16.842s）— R1 高运动信号（文本/运镜或大表情，16.842s）
- 锚点：3.37s→Clip09_first_a1.png、6.74s→Clip09_first_a2.png、10.11s→Clip09_first_a3.png、13.47s→Clip09_first_a4.png

## EP03_CLIP10（12.86s）— R1 高运动信号（文本/运镜或大表情，12.86s）
- 锚点：3.21s→Clip10_first_a1.png、6.43s→Clip10_first_a2.png、9.64s→Clip10_first_a3.png

## 跳过
- EP03_CLIP01：已有单 midframe，但命中 R1 高运动信号（文本/运镜或大表情，12.358s），升级为 continuity.anchors[]
- EP03_CLIP02：已手动声明 midframe，且未命中多锚规则，人工优先
- EP03_CLIP03：已有单 midframe，但命中 R2 普通长镜（24.531s/3拍），升级为 continuity.anchors[]
- EP03_CLIP04：已有单 midframe，但命中 R2 普通长镜（33.363s/3拍），升级为 continuity.anchors[]
- EP03_CLIP05：已手动声明 anchors，人工优先
- EP03_CLIP06：已有单 midframe，但命中 R2 普通长镜（20.956s/4拍），升级为 continuity.anchors[]
- EP03_CLIP07：已有单 midframe，但命中 R2 普通长镜（13.797s/4拍），升级为 continuity.anchors[]
- EP03_CLIP08：已有单 midframe，但命中 R1 高运动信号（文本/运镜或大表情，34.092s），升级为 continuity.anchors[]
- EP03_CLIP09：已有单 midframe，但命中 R1 高运动信号（文本/运镜或大表情，16.842s），升级为 continuity.anchors[]
- EP03_CLIP10：已有单 midframe，但命中 R1 高运动信号（文本/运镜或大表情，12.86s），升级为 continuity.anchors[]
