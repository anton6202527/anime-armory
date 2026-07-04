# 高动态/大场景制作计划

- episode: 第2集
- spectacle_clips: 3

| Clip | 类型 | 缺契约字段 | 控制输入 | 回退/保真实现方案 |
|---|---|---|---|---|
| Clip_03 | fight_exchange | - | pose_sequence, depth_sequence, instance_masks, contact_map, camera_path | 若一段内动作不稳，拆为起手/冲撞/错身/落点四张锚帧。 |
| Clip_04 | fight_exchange | - | pose_sequence, depth_sequence, instance_masks, contact_map, camera_path | 若一段内动作不稳，拆为起手/冲撞/错身/落点四张锚帧。 |
| Clip_10 | stealth_stalk | - | pose_sequence, depth_sequence, camera_path, spatial_path, parallax_layers | 若远景逼近不稳，降级为火把点阵远景 + 姜月初背影反应两个拆镜。 |
