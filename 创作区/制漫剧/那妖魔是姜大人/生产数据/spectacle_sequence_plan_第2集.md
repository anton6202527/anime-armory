# 高动态/大场景序列连续性总账

- episode: 第2集
- spectacle_clips: 4
- sequences: 2

| Sequence | 类型 | Clips | 主体 | 资产/场景 | 控制输入 | 引用策略 |
|---|---|---|---|---|---|---|
| SQ_ACTION_01 | fight_exchange | Clip_03, Clip_04 | CHAR_01, CHAR_02, CHAR_03 | CHAR_01, CHAR_02, CHAR_03, LOC_01, WEAPON_01 | camera_path, contact_map, depth_sequence, instance_masks, pose_sequence | first_passed_clip_becomes_motion_reference |
| SQ_LARGE_02 | large_establishing | Clip_08, Clip_10 | CHAR_01, CHAR_02, CHAR_03 | CHAR_01, CHAR_02, CHAR_03, LOC_01, WEAPON_01 | camera_path, depth_sequence, parallax_layers | scene_layer_pack_required |
