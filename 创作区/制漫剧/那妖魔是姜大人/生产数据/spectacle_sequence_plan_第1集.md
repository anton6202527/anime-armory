# 高动态/大场景序列连续性总账

- episode: 第1集
- spectacle_clips: 4
- sequences: 3

| Sequence | 类型 | Clips | 主体 | 资产/场景 | 控制输入 | 引用策略 |
|---|---|---|---|---|---|---|
| SQ_LARGE_01 | large_establishing | Clip_01 | CHAR_01 | CHAR_01, LOC_01 | camera_path, depth_sequence, parallax_layers | scene_layer_pack_required |
| SQ_SPECTACLE_02 | realm_portal | Clip_02 | CHAR_01, CHAR_03 | CHAR_01, CHAR_03, LOC_01 | camera_path, depth_sequence, spatial_path, vfx_layers | first_passed_clip_becomes_motion_reference |
| SQ_ACTION_03 | fight_exchange | Clip_06, Clip_10 | CHAR_01, CHAR_02, CHAR_03 | CHAR_01, CHAR_02, CHAR_03, LOC_01, WEAPON_01 | camera_path, contact_map, depth_sequence, instance_masks, pose_sequence | first_passed_clip_becomes_motion_reference |
