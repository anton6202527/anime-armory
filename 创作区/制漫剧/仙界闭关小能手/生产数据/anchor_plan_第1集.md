# 中段锚帧规划 — 第1集

- **视频后端消费计划**：backend=Seedance 2.0；channel=即梦/Dreamina；execution=dreamina；mode=native_multiframe；action=submit first/mid/end frames in one native multi-keyframe request
- 命中 Clip：0 个；新增锚帧 0 张
- **成本增量**：多出图 **0 张**（便宜）。视频成本看执行后端：**multiframe2video（即梦，首选）= 仍 1 次调用/Clip，不翻倍**；仅 frames2video-only 后端才退化为 K+1 段（共 0 段）。
- 确认后用 `--write` 注回 storyboard.json，再走 n2d-image 出 `_aK`/`_mid` 锚帧

## 跳过
- EP01_CLIP01：已手动声明 midframe/anchors，人工优先
- EP01_CLIP02：已手动声明 midframe/anchors，人工优先
- EP01_CLIP03：已手动声明 midframe/anchors，人工优先
- EP01_CLIP04：已手动声明 midframe/anchors，人工优先
- EP01_CLIP05：已手动声明 midframe/anchors，人工优先
- EP01_CLIP06：已手动声明 midframe/anchors，人工优先
- EP01_CLIP07：已手动声明 midframe/anchors，人工优先
- EP01_CLIP08：已手动声明 midframe/anchors，人工优先
- EP01_CLIP09：已手动声明 midframe/anchors，人工优先
- EP01_CLIP10：已手动声明 midframe/anchors，人工优先
- EP01_CLIP11：已手动声明 midframe/anchors，人工优先
- EP01_CLIP12：已手动声明 midframe/anchors，人工优先
