# 中段锚帧规划 — 第1集

- **视频后端消费计划**：backend=Seedance 2.0；channel=即梦/Dreamina；execution=dreamina；mode=native_multiframe；action=submit first/mid/end frames in one native multi-keyframe request
- 命中 Clip：6 个；新增锚帧 9 张
- **成本增量**：多出图 **9 张**（便宜）。视频成本看执行后端：连续动作可用 native multiframe 保持 1 次调用，或用 split relay 变 K+1 段；E1 编辑切点本来就是独立 take，不得为省调用合回一条。当前新增物理边界/分段计数 9。
- 确认后用 `--write` 注回 storyboard.json，再走 n2d-image 出 `_aK`/`_mid` 锚帧

## EP01_CLIP01（4.553s）— E1 storyboard 多镜位硬切边界
- 锚点：2.7s→EP01_CLIP01_a1.png

## EP01_CLIP02（7.1s）— E1 storyboard 多镜位硬切边界
- 锚点：4.8s→EP01_CLIP02_a1.png、6.1s→EP01_CLIP02_a2.png

## EP01_CLIP04（8.267s）— E1 storyboard 多镜位硬切边界
- 锚点：3.8s→EP01_CLIP04_a1.png、5.4s→EP01_CLIP04_a2.png

## EP01_CLIP05（4.336s）— E1 storyboard 多镜位硬切边界
- 锚点：2.5s→EP01_CLIP05_a1.png

## EP01_CLIP06（7.558s）— E1 storyboard 多镜位硬切边界
- 锚点：2.0s→EP01_CLIP06_a1.png、4.5s→EP01_CLIP06_a2.png

## EP01_CLIP07（4.339s）— E1 storyboard 多镜位硬切边界
- 锚点：2.4s→EP01_CLIP07_a1.png

## 跳过
- EP01_CLIP03：已手动声明 anchors，人工优先
- EP01_CLIP04：已有 midframe/anchors 但时间越界或不可解析，按当前 duration 重算
- EP01_CLIP06：已有 midframe/anchors 但时间越界或不可解析，按当前 duration 重算
