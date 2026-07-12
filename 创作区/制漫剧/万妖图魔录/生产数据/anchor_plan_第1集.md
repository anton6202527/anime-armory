# 中段锚帧规划 — 第1集

- **视频后端消费计划**：backend=未固定；channel=未固定；execution=unknown；mode=unknown_manual_confirm；action=manual confirmation required before paid generation
- 命中 Clip：0 个；新增锚帧 0 张
- **成本增量**：多出图 **0 张**（便宜）。视频成本看执行后端：连续动作可用 native multiframe 保持 1 次调用，或用 split relay 变 K+1 段；E1 编辑切点本来就是独立 take，不得为省调用合回一条。当前新增物理边界/分段计数 0。
- 确认后用 `--write` 注回 storyboard.json，再走 n2d-image 出 `_aK`/`_mid` 锚帧

## 跳过
- EP01_CLIP01：已手动声明 anchors，人工优先
- EP01_CLIP04：已手动声明 anchors，人工优先
- EP01_CLIP05：已手动声明 anchors，人工优先
- EP01_CLIP06：已手动声明 anchors，人工优先
- EP01_CLIP07：已手动声明 anchors，人工优先
- EP01_CLIP08：已手动声明 anchors，人工优先
- EP01_CLIP10：已手动声明 anchors，人工优先
- EP01_CLIP11：已手动声明 anchors，人工优先
- EP01_CLIP13：已手动声明 anchors，人工优先
- EP01_CLIP17：已手动声明 anchors，人工优先
