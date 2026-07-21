# 中段锚帧规划 — 第1集

- **视频后端消费计划**：backend=未固定；channel=未固定；execution=unknown；mode=unknown_manual_confirm；action=manual confirmation required before paid generation
- 命中 Clip：5 个；新增锚帧 8 张
- **成本增量**：多出图 **8 张**（便宜）。视频成本看执行后端：连续动作可用 native multiframe 保持 1 次调用，或用 split relay 变 K+1 段；E1 编辑切点本来就是独立 take，不得为省调用合回一条。当前新增物理边界/分段计数 8。
- 确认后用 `--write` 注回 storyboard.json，再走 n2d-image 出 `_aK`/`_mid` 锚帧

## EP01_CLIP02（11.52s）— R2 普通长镜（11.52s/4拍）
- 锚点：5.76s→EP01_CLIP02_a1.png

## EP01_CLIP03（11.989s）— R2 普通长镜（11.989s/4拍）
- 锚点：5.99s→EP01_CLIP03_a1.png

## EP01_CLIP05（11.608s）— R1 高运动信号（文本/运镜或大表情，11.608s）
- 锚点：3.87s→EP01_CLIP05_a1.png、7.74s→EP01_CLIP05_a2.png

## EP01_CLIP07（10.811s）— R1 高运动信号（文本/运镜或大表情，10.811s）
- 锚点：3.6s→EP01_CLIP07_a1.png、7.21s→EP01_CLIP07_a2.png

## EP01_CLIP08（9.316s）— E1 storyboard 多镜位硬切边界
- 锚点：3.6s→EP01_CLIP08_a1.png、7.0s→EP01_CLIP08_a2.png

## 跳过
- EP01_CLIP01：已手动声明 anchors，人工优先
- EP01_CLIP02：已有自动 anchors 但源时长已变或缺 source_duration，按当前 duration 重算
- EP01_CLIP02：已有 midframe/anchors 但时间越界或不可解析，按当前 duration 重算
- EP01_CLIP03：已有自动 anchors 但源时长已变或缺 source_duration，按当前 duration 重算
- EP01_CLIP03：已有 midframe/anchors 但时间越界或不可解析，按当前 duration 重算
- EP01_CLIP04：已手动声明 anchors，人工优先
- EP01_CLIP05：已有自动 anchors 但源时长已变或缺 source_duration，按当前 duration 重算
- EP01_CLIP05：已有 midframe/anchors 但时间越界或不可解析，按当前 duration 重算
- EP01_CLIP06：已手动声明 anchors，人工优先
- EP01_CLIP07：已有自动 anchors 但源时长已变或缺 source_duration，按当前 duration 重算
- EP01_CLIP07：已有 midframe/anchors 但时间越界或不可解析，按当前 duration 重算
- EP01_CLIP08：已有 midframe/anchors 但时间越界或不可解析，按当前 duration 重算
