# 高动态/大场景序列连续性总账

- episode: 第1集
- spectacle_clips: 6
- sequences: 4

| Sequence | 类型 | Clips | 主体 | 资产/场景 | 控制输入 | 引用策略 |
|---|---|---|---|---|---|---|
| SQ_LARGE_01 | large_establishing | Clip_01 | CHAR_GARRISON_SURVIVORS, CHAR_JIANG_YUECHU | CHAR_GARRISON_SURVIVORS, CHAR_JIANG_YUECHU, LOC_BAXI_BATTLEFIELD, LOC_BAXI_BATTLEFIELD_ESTABLISH, WEAPON_DAHUANG_HALBERD | camera_path, depth_sequence, parallax_layers | scene_layer_pack_required |
| SQ_ACTION_02 | magic_burst | Clip_02 | CHAR_JIANG_YUECHU | CHAR_JIANG_YUECHU, LOC_BAXI_BATTLEFIELD, VFX_ESSENCE_STREAMS, VFX_SYSTEM_PANEL, VFX_WHITE_QI, WEAPON_DAHUANG_HALBERD | camera_path, depth_sequence, parallax_layers, spatial_path, vfx_layers | first_passed_clip_becomes_motion_reference |
| SQ_SPECTACLE_03 | meditation_cultivation | Clip_03, Clip_08 | CHAR_JIANG_YUECHU | CHAR_JIANG_YUECHU, LOC_BAXI_BATTLEFIELD, LOC_BROKEN_HOUSE, LOC_CONSCIOUSNESS_SEA, VFX_RED_FLOOD_DRAGON_SCROLL, VFX_YINSHAN_MIST, WEAPON_DAHUANG_HALBERD | depth_sequence, pose_sequence, vfx_layers | first_passed_clip_becomes_motion_reference |
| SQ_ACTION_04 | magic_burst | Clip_11, Clip_13 | CHAR_JIANG_YUECHU | CHAR_JIANG_YUECHU, LOC_BROKEN_HOUSE, LOC_CONSCIOUSNESS_SEA, VFX_SYSTEM_PANEL, VFX_THREE_DRAGON_ORBS, VFX_YINSHAN_MIST | camera_path, depth_sequence, parallax_layers, spatial_path, vfx_layers | first_passed_clip_becomes_motion_reference |
