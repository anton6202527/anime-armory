# 高动态/大场景制作计划

- episode: 第3集
- spectacle_clips: 3

| Clip | 类型 | 缺契约字段 | 控制输入 | 回退/保真实现方案 |
|---|---|---|---|---|
| Clip_02 | large_establishing | - | camera_path, depth_sequence, parallax_layers | 若全景空间不稳，先出静态建立帧，再拆为前景动作特写 + 场景空镜，保持同一光位和轴线。 |
| Clip_03 | large_establishing | - | camera_path, depth_sequence, parallax_layers | 若全景空间不稳，先出静态建立帧，再拆为前景动作特写 + 场景空镜，保持同一光位和轴线。 |
| Clip_05 | mount_ride | - | pose_sequence, depth_sequence, instance_masks, contact_map, camera_path, spatial_path, parallax_layers | 若完整马队不稳，拆为火把远景、马蹄停下、陈青源下马三帧。 |
