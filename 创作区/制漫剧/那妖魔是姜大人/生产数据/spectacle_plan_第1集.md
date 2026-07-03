# 高动态/大场景制作计划

- episode: 第1集
- spectacle_clips: 4

| Clip | 类型 | 缺契约字段 | 控制输入 | 回退/保真实现方案 |
|---|---|---|---|---|
| Clip_01 | large_establishing | - | camera_path, depth_sequence, parallax_layers | 先出静态全景关键帧，再做慢推/横移/分层 parallax；复杂人群改剪影或分层合成。 |
| Clip_02 | realm_portal | - | depth_sequence, camera_path, spatial_path, vfx_layers | 若一镜内认知和显景不稳，拆成囚服特写、尸场全景、虎妖尸身远景三张锚帧。 |
| Clip_06 | fight_exchange | - | pose_sequence, depth_sequence, instance_masks, contact_map, camera_path | 若双主体接触不稳，拆为裴起手单人镜、虎妖脚掌命中特写、裴倒飞受击反应三段。 |
| Clip_10 | fight_exchange | - | pose_sequence, depth_sequence, instance_masks, contact_map, camera_path | 若接触镜不稳，拆为姜月初道歉脸部、横刀刀柄推进手部、裴长青眼睛僵住三个特写。 |
