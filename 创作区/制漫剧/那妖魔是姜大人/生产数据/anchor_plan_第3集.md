# 中段锚帧规划 — 第3集

- **视频后端消费计划**：backend=Seedance 2.0；channel=即梦/Dreamina；execution=dreamina；mode=native_multiframe；action=submit first/mid/end frames in one native multi-keyframe request
- 命中 Clip：1 个；新增锚帧 3 张
- **成本增量**：多出图 **3 张**（便宜）。视频成本看执行后端：连续动作可用 native multiframe 保持 1 次调用，或用 split relay 变 K+1 段；E1 编辑切点本来就是独立 take，不得为省调用合回一条。当前新增物理边界/分段计数 3。
- 确认后用 `--write` 注回 storyboard.json，再走 n2d-image 出 `_aK`/`_mid` 锚帧

## EP03_CLIP06（12.5s）— R1 高运动信号（文本/运镜或大表情，12.5s）
- 锚点：3.12s→EP03_CLIP06_a1.png、6.25s→EP03_CLIP06_a2.png、9.38s→EP03_CLIP06_a3.png

## 跳过
- EP03_CLIP03：已手动声明 anchors，人工优先
- EP03_CLIP07：已手动声明 anchors，人工优先
- EP03_CLIP08：已手动声明 anchors，人工优先
