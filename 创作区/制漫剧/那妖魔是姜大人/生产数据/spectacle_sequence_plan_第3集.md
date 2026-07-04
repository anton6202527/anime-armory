# 高动态/大场景序列连续性总账

- episode: 第3集
- spectacle_clips: 3
- sequences: 2

| Sequence | 类型 | Clips | 主体 | 资产/场景 | 控制输入 | 引用策略 |
|---|---|---|---|---|---|---|
| SQ_LARGE_01 | large_establishing | Clip_02, Clip_03 | CHAR_01, CHAR_02, CHAR_04 | CHAR_01, CHAR_02, CHAR_04, LOC_01, LOC_02, WEAPON_01 | camera_path, depth_sequence, parallax_layers | scene_layer_pack_required |
| SQ_ACTION_02 | mount_ride | Clip_05 | CHAR_01, CHAR_04 | CHAR_01, CHAR_04, LOC_01, LOC_02, MOUNT_GROUP_01 | camera_path, contact_map, depth_sequence, instance_masks, parallax_layers, pose_sequence, spatial_path | first_passed_clip_becomes_motion_reference |
