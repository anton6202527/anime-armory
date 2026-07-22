# 第1集 视频帧级脸漂观察包

- 状态：ready_for_human_frame_identity_review
- 母版：`出视频/第1集/视频/Clip_08_对不住了，刀落人身_part1.mp4`
- 时间范围：0.0s - 3.966s；间隔 0.5s
- contact sheet：`生产数据/video_face_drift_watch_第1集_Clip_08___part1_0.00_3.97s.jpg`

## 判定口径

- 这不是正式验收，只是把最终 MP4 的近景脸漂做成人审证据。
- 任一主角/核心角色清晰近脸看起来不是同一角色，按脸漂 block 记录，不能签收成通过。
- 修法优先回 `n2d-video` 废料重跑；若是从小脸/远脸升格成近脸，先回 `n2d-image` 补同源近景锚帧/表情参考并过 full image_qc。

## 抽帧

- 0.0s / Clip_08_part1 / `生产数据/video_face_drift_watch/第1集/Clip_08___part1_0.00_3.97s/001_Clip_08_part1_000.000s.jpg`
- 0.5s / Clip_08_part1 / `生产数据/video_face_drift_watch/第1集/Clip_08___part1_0.00_3.97s/002_Clip_08_part1_000.500s.jpg`
- 1.0s / Clip_08_part1 / `生产数据/video_face_drift_watch/第1集/Clip_08___part1_0.00_3.97s/003_Clip_08_part1_001.000s.jpg`
- 1.5s / Clip_08_part1 / `生产数据/video_face_drift_watch/第1集/Clip_08___part1_0.00_3.97s/004_Clip_08_part1_001.500s.jpg`
- 2.0s / Clip_08_part1 / `生产数据/video_face_drift_watch/第1集/Clip_08___part1_0.00_3.97s/005_Clip_08_part1_002.000s.jpg`
- 2.5s / Clip_08_part1 / `生产数据/video_face_drift_watch/第1集/Clip_08___part1_0.00_3.97s/006_Clip_08_part1_002.500s.jpg`
- 3.0s / Clip_08_part1 / `生产数据/video_face_drift_watch/第1集/Clip_08___part1_0.00_3.97s/007_Clip_08_part1_003.000s.jpg`
- 3.5s / Clip_08_part1 / `生产数据/video_face_drift_watch/第1集/Clip_08___part1_0.00_3.97s/008_Clip_08_part1_003.500s.jpg`
