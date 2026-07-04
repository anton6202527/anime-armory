# 无成本图片生产包

- episode: 第3集
- reference_generation_tasks: 8
- keyshot_candidate_tasks: 13
- regional_construct_manifests: 2
- shot_packages: 13

## P0 参考资产补图

| Task | Priority | Owner | Slot | Output |
|---|---|---|---|---|
| REF_007 | P0 | CHAR_HE_PINGSHENG/常态 | expression_bank | 出图/共享/图片/定妆_贺平生_表情_克制.png |
| REF_008 | P0 | CHAR_HE_PINGSHENG/常态 | action_pose_pack | 出图/共享/图片/定妆_CHAR_HE_PINGSHENG_常态_action_pose_pack.png |
| REF_015 | P0 | CHAR_ZHANG_LAODA/常态 | expression_bank | 出图/共享/图片/定妆_张老大.png |
| REF_016 | P0 | CHAR_ZHANG_LAODA/常态 | action_pose_pack | 出图/共享/图片/定妆_CHAR_ZHANG_LAODA_常态_action_pose_pack.png |
| REF_066 | P0 | Clip_05 | regional_construct_plate | 出图/第3集/区域构建/Clip_05/empty_plate.png |
| REF_067 | P0 | Clip_05 | region_masks | 出图/第3集/区域构建/Clip_05/masks.json |
| REF_068 | P0 | Clip_06 | regional_construct_plate | 出图/第3集/区域构建/Clip_06/empty_plate.png |
| REF_069 | P0 | Clip_06 | region_masks | 出图/第3集/区域构建/Clip_06/masks.json |

## 关键镜候选

| Clip | Tags | N | Status | Best |
|---|---|---:|---|---|
| Clip_01 | opening、hook_or_payoff、multi_subject、strong_emotion | 6 | needs_generation | - |
| Clip_02 | multi_subject、strong_emotion | 5 | needs_generation | - |
| Clip_03 | hook_or_payoff、multi_subject、strong_emotion | 5 | needs_generation | - |
| Clip_04 | multi_subject、strong_emotion | 5 | needs_generation | - |
| Clip_05 | multi_subject、strong_emotion | 5 | needs_generation | - |
| Clip_06 | multi_subject、strong_emotion | 5 | needs_generation | - |
| Clip_07 | multi_subject、strong_emotion | 5 | needs_generation | - |
| Clip_08 | hook_or_payoff、multi_subject、strong_emotion | 5 | needs_generation | - |
| Clip_09 | multi_subject、strong_emotion | 5 | needs_generation | - |
| Clip_10 | hook_or_payoff、multi_subject、strong_emotion | 5 | needs_generation | - |
| Clip_11 | hook_or_payoff、multi_subject、strong_emotion | 5 | needs_generation | - |
| Clip_12 | multi_subject | 5 | needs_generation | - |
| Clip_13 | multi_subject | 5 | needs_generation | - |

## 多人同框分区构建

| Clip | Mode | Manifest | Steps |
|---|---|---|---|
| Clip_05 | regional_construct_required | 出图/第3集/区域构建/Clip_05/regional_construct_manifest.json | generate_empty_plate_without_characters → create_region_masks_per_slot → inpaint_each_slot_with_own_reference_group → relighting_color_match → final_qc_identity_slots |
| Clip_06 | regional_construct_required | 出图/第3集/区域构建/Clip_06/regional_construct_manifest.json | generate_empty_plate_without_characters → create_region_masks_per_slot → inpaint_each_slot_with_own_reference_group → relighting_color_match → final_qc_identity_slots |
