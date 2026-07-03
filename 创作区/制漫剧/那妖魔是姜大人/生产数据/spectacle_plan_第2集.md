# 高动态/大场景制作计划

- episode: 第2集
- spectacle_clips: 4

| Clip | 类型 | 缺契约字段 | 控制输入 | 回退/保真实现方案 |
|---|---|---|---|---|
| Clip_03 | fight_exchange | - | pose_sequence, depth_sequence, instance_masks, contact_map, camera_path | 若一段内动作不稳，拆为起手/冲撞/错身/落点四张锚帧。 |
| Clip_04 | fight_exchange | - | pose_sequence, depth_sequence, instance_masks, contact_map, camera_path | 若一段内动作不稳，拆为起手/冲撞/错身/落点四张锚帧。 |
| Clip_08 | large_establishing | - | camera_path, depth_sequence, parallax_layers | 先出静态全景关键帧，再做慢推/横移/分层 parallax；复杂人群改剪影或分层合成。 |
| Clip_10 | large_establishing | - | camera_path, depth_sequence, parallax_layers | 先出静态全景关键帧，再做慢推/横移/分层 parallax；复杂人群改剪影或分层合成。 |
