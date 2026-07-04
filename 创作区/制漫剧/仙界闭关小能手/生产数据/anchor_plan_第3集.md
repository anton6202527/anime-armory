# 中段锚帧规划 — 第3集

- **视频后端消费计划**：backend=Seedance 2.0；channel=即梦/Dreamina；execution=dreamina；mode=native_multiframe；action=submit first/mid/end frames in one native multi-keyframe request
- 命中 Clip：0 个；新增锚帧 0 张
- **成本增量**：多出图 **0 张**（便宜）。视频成本看执行后端：**multiframe2video（即梦，首选）= 仍 1 次调用/Clip，不翻倍**；仅 frames2video-only 后端才退化为 K+1 段（共 0 段）。
- 确认后用 `--write` 注回 storyboard.json，再走 n2d-image 出 `_aK`/`_mid` 锚帧

## 跳过
- Clip_01：已手动声明 anchors，人工优先
- Clip_02：已手动声明 anchors，人工优先
- Clip_03：已手动声明 anchors，人工优先
- Clip_04：已手动声明 anchors，人工优先
- Clip_05：已手动声明 anchors，人工优先
- Clip_06：已手动声明 anchors，人工优先
- Clip_07：已手动声明 anchors，人工优先
- Clip_08：已手动声明 anchors，人工优先
- Clip_09：已手动声明 anchors，人工优先
- Clip_10：已手动声明 anchors，人工优先
- Clip_11：已手动声明 anchors，人工优先
- Clip_12：已手动声明 anchors，人工优先
- Clip_13：已手动声明 anchors，人工优先
