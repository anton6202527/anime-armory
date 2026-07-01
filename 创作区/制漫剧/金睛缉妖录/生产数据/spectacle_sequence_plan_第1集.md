# 高动态/大场景序列连续性总账

- episode: 第1集
- spectacle_clips: 4
- sequences: 2

| Sequence | 类型 | Clips | 主体 | 资产/场景 | 控制输入 | 引用策略 |
|---|---|---|---|---|---|---|
| SQ_SPECTACLE_01 | evidence_search | Clip_01, Clip_03 | CHAR_PI_DEMON_CHENGUI, CHAR_SHEN_YAN | CHAR_PI_DEMON_CHENGUI, CHAR_SHEN_YAN, LOC_CHEN_HOUSE, PROP_BLOOD_THRESHOLD, PROP_CLEAN_BLACK_BOOT, PROP_MUD_FOOTPRINT, PROP_STILL_TEA | - | first_passed_clip_becomes_motion_reference |
| SQ_ACTION_02 | mixed_action | Clip_10, Clip_11 | CHAR_PEIJUE, CHAR_PI_DEMON_CHENGUI, CHAR_SHEN_YAN | CHAR_PEIJUE, CHAR_PI_DEMON_CHENGUI, CHAR_SHEN_YAN, LOC_CHEN_HOUSE, VFX_JINJING_GOLD_EYE, VFX_PEIJUE_FU_FIRE, VFX_SKIN_DEMON_REVEAL | camera_path, contact_map, depth_sequence, instance_masks, parallax_layers, pose_sequence, spatial_path, vfx_layers | first_passed_clip_becomes_motion_reference |
