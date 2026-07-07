# 第1集 视频帧级脸漂观察包

- 状态：ready_for_human_frame_identity_review
- 母版：`合成/第1集/成片_第1集_zh.mp4`
- 时间范围：66.8s - 85.0s；间隔 0.5s
- contact sheet：`生产数据/video_face_drift_watch_第1集_66.80_85.00s.jpg`

## 判定口径

- 这不是正式验收，只是把最终 MP4 的近景脸漂做成人审证据。
- 任一主角/核心角色清晰近脸看起来不是同一角色，按脸漂 block 记录，不能签收成通过。
- 修法优先回 `n2d-video` 废料重跑；若是从小脸/远脸升格成近脸，先回 `n2d-image` 补同源近景锚帧/表情参考并过 full image_qc。

## 抽帧

- 66.8s / Clip_05 / `生产数据/video_face_drift_watch/第1集/66.80_85.00s/001_Clip_05_066.800s.jpg`
- 67.3s / Clip_05 / `生产数据/video_face_drift_watch/第1集/66.80_85.00s/002_Clip_05_067.300s.jpg`
- 67.8s / Clip_06 / `生产数据/video_face_drift_watch/第1集/66.80_85.00s/003_Clip_06_067.800s.jpg`
- 68.3s / Clip_06 / `生产数据/video_face_drift_watch/第1集/66.80_85.00s/004_Clip_06_068.300s.jpg`
- 68.8s / Clip_06 / `生产数据/video_face_drift_watch/第1集/66.80_85.00s/005_Clip_06_068.800s.jpg`
- 69.3s / Clip_06 / `生产数据/video_face_drift_watch/第1集/66.80_85.00s/006_Clip_06_069.300s.jpg`
- 69.8s / Clip_06 / `生产数据/video_face_drift_watch/第1集/66.80_85.00s/007_Clip_06_069.800s.jpg`
- 70.3s / Clip_06 / `生产数据/video_face_drift_watch/第1集/66.80_85.00s/008_Clip_06_070.300s.jpg`
- 70.8s / Clip_06 / `生产数据/video_face_drift_watch/第1集/66.80_85.00s/009_Clip_06_070.800s.jpg`
- 71.3s / Clip_06 / `生产数据/video_face_drift_watch/第1集/66.80_85.00s/010_Clip_06_071.300s.jpg`
- 71.8s / Clip_06 / `生产数据/video_face_drift_watch/第1集/66.80_85.00s/011_Clip_06_071.800s.jpg`
- 72.3s / Clip_06 / `生产数据/video_face_drift_watch/第1集/66.80_85.00s/012_Clip_06_072.300s.jpg`
- 72.8s / Clip_06 / `生产数据/video_face_drift_watch/第1集/66.80_85.00s/013_Clip_06_072.800s.jpg`
- 73.3s / Clip_06 / `生产数据/video_face_drift_watch/第1集/66.80_85.00s/014_Clip_06_073.300s.jpg`
- 73.8s / Clip_06 / `生产数据/video_face_drift_watch/第1集/66.80_85.00s/015_Clip_06_073.800s.jpg`
- 74.3s / Clip_06 / `生产数据/video_face_drift_watch/第1集/66.80_85.00s/016_Clip_06_074.300s.jpg`
- 74.8s / Clip_06 / `生产数据/video_face_drift_watch/第1集/66.80_85.00s/017_Clip_06_074.800s.jpg`
- 75.3s / Clip_06 / `生产数据/video_face_drift_watch/第1集/66.80_85.00s/018_Clip_06_075.300s.jpg`
- 75.8s / Clip_06 / `生产数据/video_face_drift_watch/第1集/66.80_85.00s/019_Clip_06_075.800s.jpg`
- 76.3s / Clip_06 / `生产数据/video_face_drift_watch/第1集/66.80_85.00s/020_Clip_06_076.300s.jpg`
- 76.8s / Clip_06 / `生产数据/video_face_drift_watch/第1集/66.80_85.00s/021_Clip_06_076.800s.jpg`
- 77.3s / Clip_06 / `生产数据/video_face_drift_watch/第1集/66.80_85.00s/022_Clip_06_077.300s.jpg`
- 77.8s / Clip_06 / `生产数据/video_face_drift_watch/第1集/66.80_85.00s/023_Clip_06_077.800s.jpg`
- 78.3s / Clip_06 / `生产数据/video_face_drift_watch/第1集/66.80_85.00s/024_Clip_06_078.300s.jpg`
- 78.8s / Clip_06 / `生产数据/video_face_drift_watch/第1集/66.80_85.00s/025_Clip_06_078.800s.jpg`
- 79.3s / Clip_06 / `生产数据/video_face_drift_watch/第1集/66.80_85.00s/026_Clip_06_079.300s.jpg`
- 79.8s / Clip_06 / `生产数据/video_face_drift_watch/第1集/66.80_85.00s/027_Clip_06_079.800s.jpg`
- 80.3s / Clip_06 / `生产数据/video_face_drift_watch/第1集/66.80_85.00s/028_Clip_06_080.300s.jpg`
- 80.8s / Clip_06 / `生产数据/video_face_drift_watch/第1集/66.80_85.00s/029_Clip_06_080.800s.jpg`
- 81.3s / Clip_06 / `生产数据/video_face_drift_watch/第1集/66.80_85.00s/030_Clip_06_081.300s.jpg`
- 81.8s / Clip_06 / `生产数据/video_face_drift_watch/第1集/66.80_85.00s/031_Clip_06_081.800s.jpg`
- 82.3s / Clip_07 / `生产数据/video_face_drift_watch/第1集/66.80_85.00s/032_Clip_07_082.300s.jpg`
- 82.8s / Clip_07 / `生产数据/video_face_drift_watch/第1集/66.80_85.00s/033_Clip_07_082.800s.jpg`
- 83.3s / Clip_07 / `生产数据/video_face_drift_watch/第1集/66.80_85.00s/034_Clip_07_083.300s.jpg`
- 83.8s / Clip_07 / `生产数据/video_face_drift_watch/第1集/66.80_85.00s/035_Clip_07_083.800s.jpg`
- 84.3s / Clip_07 / `生产数据/video_face_drift_watch/第1集/66.80_85.00s/036_Clip_07_084.300s.jpg`
- 84.8s / Clip_07 / `生产数据/video_face_drift_watch/第1集/66.80_85.00s/037_Clip_07_084.800s.jpg`
