# 中段锚帧规划 — 第1集

- **视频后端消费计划**：backend=未固定；channel=未固定；execution=unknown；mode=unknown_manual_confirm；action=manual confirmation required before paid generation
- 命中 Clip：4 个；新增锚帧 11 张
- **成本增量**：多出图 **11 张**（便宜）。视频成本看执行后端：连续动作可用 native multiframe 保持 1 次调用，或用 split relay 变 K+1 段；E1 编辑切点本来就是独立 take，不得为省调用合回一条。当前新增物理边界/分段计数 11。
- 确认后用 `--write` 注回 storyboard.json，再走 n2d-image 出 `_aK`/`_mid` 锚帧

## EP01_CLIP05（8.67s）— E1 storyboard 多镜位硬切边界
- 锚点：3.2s→Clip05_first_a1.png、5.7s→Clip05_first_a2.png、8.37s→Clip05_first_a3.png

## EP01_CLIP07（12.677s）— E1 storyboard 多镜位硬切边界
- 锚点：3.6s→Clip07_first_a1.png、8.4s→Clip07_first_a2.png、12.58s→Clip07_first_a3.png

## EP01_CLIP08（10.228s）— E1 storyboard 多镜位硬切边界
- 锚点：4.9s→Clip08_first_a1.png、9.48s→Clip08_first_a2.png

## EP01_CLIP13（7.946s）— E1 storyboard 多镜位硬切边界
- 锚点：2.2s→Clip13_first_a1.png、5.0s→Clip13_first_a2.png、7.75s→Clip13_first_a3.png

## 跳过
- EP01_CLIP01：已手动声明 anchors，人工优先
- EP01_CLIP02：已手动声明 anchors，人工优先
- EP01_CLIP03：已手动声明 anchors，人工优先
- EP01_CLIP04：已手动声明 anchors，人工优先
- EP01_CLIP05：已有 midframe/anchors 但时间越界或不可解析，按当前 duration 重算
- EP01_CLIP06：已手动声明 anchors，人工优先
- EP01_CLIP07：已有 midframe/anchors 但时间越界或不可解析，按当前 duration 重算
- EP01_CLIP08：已有 midframe/anchors 但时间越界或不可解析，按当前 duration 重算
- EP01_CLIP09：已手动声明 anchors，人工优先
- EP01_CLIP10：已手动声明 anchors，人工优先
- EP01_CLIP11：已手动声明 anchors，人工优先
- EP01_CLIP12：已手动声明 anchors，人工优先
- EP01_CLIP13：已有 midframe/anchors 但时间越界或不可解析，按当前 duration 重算
- EP01_CLIP14：已手动声明 anchors，人工优先
- EP01_CLIP15：已手动声明 anchors，人工优先
