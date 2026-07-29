# 无成本图片生产包

- episode: 第3集
- reference_generation_tasks: 27
- keyshot_candidate_tasks: 6
- regional_construct_manifests: 5
- shot_packages: 8

## P0 参考资产补图

| Task | Priority | Owner | Slot | Output |
|---|---|---|---|---|
| REF_010 | P0 | CHAR_01/“囚途残损态” | action_pose_pack | 出图/共享/图片/定妆_CHAR_01_“囚途残损态”_action_pose_pack.png |
| REF_020 | P0 | CHAR_01/镇魔司制服态 | action_pose_pack | 出图/共享/图片/定妆_CHAR_01_镇魔司制服态_action_pose_pack.png |
| REF_024 | P0 | CHAR_03/常态 | rear_three_quarter | 出图/共享/图片/定妆_CHAR_03__常态_后45度.png |
| REF_028 | P0 | CHAR_03/常态 | expression_bank | 出图/共享/图片/定妆_CHAR_03__常态_脸部特写_脸锚裁切.png |
| REF_029 | P0 | CHAR_03/常态 | action_pose_pack | 出图/共享/图片/定妆_CHAR_03_常态_action_pose_pack.png |
| REF_037 | P0 | CHAR_02/“濒死重伤态” | expression_bank | 出图/共享/图片/定妆_CHAR_02__濒死重伤态_表情_克制.png |
| REF_038 | P0 | CHAR_02/“濒死重伤态” | action_pose_pack | 出图/共享/图片/定妆_CHAR_02_“濒死重伤态”_action_pose_pack.png |
| REF_046 | P0 | BEAST_01/“穿心复生态” | expression_bank | 出图/共享/图片/定妆_BEAST_01__穿心复生态_表情_克制.png |
| REF_047 | P0 | BEAST_01/“穿心复生态” | action_pose_pack | 出图/共享/图片/定妆_BEAST_01_“穿心复生态”_action_pose_pack.png |
| REF_062 | P0 | EP03_CLIP01 | regional_construct_plate | 出图/第3集/区域构建/EP03_CLIP01/empty_plate.png |
| REF_063 | P0 | EP03_CLIP01 | region_masks | 出图/第3集/区域构建/EP03_CLIP01/masks.json |
| REF_064 | P0 | EP03_CLIP03 | regional_construct_plate | 出图/第3集/区域构建/EP03_CLIP03/empty_plate.png |
| REF_065 | P0 | EP03_CLIP03 | region_masks | 出图/第3集/区域构建/EP03_CLIP03/masks.json |
| REF_066 | P0 | EP03_CLIP05 | regional_construct_plate | 出图/第3集/区域构建/EP03_CLIP05/empty_plate.png |
| REF_067 | P0 | EP03_CLIP05 | region_masks | 出图/第3集/区域构建/EP03_CLIP05/masks.json |
| REF_068 | P0 | EP03_CLIP06 | regional_construct_plate | 出图/第3集/区域构建/EP03_CLIP06/empty_plate.png |
| REF_069 | P0 | EP03_CLIP06 | region_masks | 出图/第3集/区域构建/EP03_CLIP06/masks.json |
| REF_070 | P0 | EP03_CLIP07 | regional_construct_plate | 出图/第3集/区域构建/EP03_CLIP07/empty_plate.png |
| REF_071 | P0 | EP03_CLIP07 | region_masks | 出图/第3集/区域构建/EP03_CLIP07/masks.json |
| REF_072 | P0 | EP03_CLIP08 | regional_construct_plate | 出图/第3集/区域构建/EP03_CLIP08/empty_plate.png |
| REF_073 | P0 | EP03_CLIP08 | region_masks | 出图/第3集/区域构建/EP03_CLIP08/masks.json |
| REF_050 | P1 | LOC_02 | empty_plate | 出图/共享/图片/定妆_LOC_02_empty_plate.png |
| REF_051 | P1 | LOC_02 | lighting_plate | 出图/共享/图片/定妆_LOC_02_lighting_plate.png |
| REF_054 | P1 | WEAPON_横刀 | detail_closeup | 出图/共享/图片/定妆_WEAPON_横刀_detail_closeup.png |
| REF_057 | P1 | LOC_01 | empty_plate | 出图/共享/图片/定妆_LOC_01_empty_plate.png |
| REF_058 | P1 | LOC_01 | lighting_plate | 出图/共享/图片/定妆_LOC_01_lighting_plate.png |
| REF_061 | P1 | PROP_镇魔司制服 | detail_closeup | 出图/共享/图片/定妆_PROP_镇魔司制服_detail_closeup.png |

## 关键镜候选

| Clip | Tags | N | Status | Best |
|---|---|---:|---|---|
| EP03_CLIP01 | opening、hook_or_payoff、multi_subject、strong_emotion | 6 | needs_generation | - |
| EP03_CLIP03 | multi_subject | 5 | needs_generation | - |
| EP03_CLIP05 | hook_or_payoff、multi_subject | 5 | needs_generation | - |
| EP03_CLIP06 | hook_or_payoff、multi_subject | 5 | needs_generation | - |
| EP03_CLIP07 | opening、hook_or_payoff、multi_subject、strong_emotion、action | 6 | needs_generation | - |
| EP03_CLIP08 | opening、hook_or_payoff、strong_emotion | 6 | needs_generation | - |

## 多人同框分区构建

| Clip | Mode | Manifest | Steps |
|---|---|---|---|
| EP03_CLIP01 | regional_construct_required | 出图/第3集/区域构建/EP03_CLIP01/regional_construct_manifest.json | generate_empty_plate_without_characters → create_region_masks_per_slot → inpaint_each_slot_with_own_reference_group → relighting_color_match → final_qc_identity_slots |
| EP03_CLIP05 | regional_construct_required | 出图/第3集/区域构建/EP03_CLIP05/regional_construct_manifest.json | generate_empty_plate_without_characters → create_region_masks_per_slot → inpaint_each_slot_with_own_reference_group → relighting_color_match → final_qc_identity_slots |
| EP03_CLIP06 | regional_construct_required | 出图/第3集/区域构建/EP03_CLIP06/regional_construct_manifest.json | generate_empty_plate_without_characters → create_region_masks_per_slot → inpaint_each_slot_with_own_reference_group → relighting_color_match → final_qc_identity_slots |
| EP03_CLIP07 | regional_construct_required | 出图/第3集/区域构建/EP03_CLIP07/regional_construct_manifest.json | generate_empty_plate_without_characters → create_region_masks_per_slot → inpaint_each_slot_with_own_reference_group → relighting_color_match → final_qc_identity_slots |
| EP03_CLIP08 | regional_construct_required | 出图/第3集/区域构建/EP03_CLIP08/regional_construct_manifest.json | generate_empty_plate_without_characters → create_region_masks_per_slot → inpaint_each_slot_with_own_reference_group → relighting_color_match → final_qc_identity_slots |
