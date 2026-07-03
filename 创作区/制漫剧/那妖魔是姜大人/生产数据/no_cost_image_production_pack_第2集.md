# 无成本图片生产包

- episode: 第2集
- reference_generation_tasks: 22
- keyshot_candidate_tasks: 10
- regional_construct_manifests: 8
- shot_packages: 10

## P0 参考资产补图

| Task | Priority | Owner | Slot | Output |
|---|---|---|---|---|
| REF_007 | P0 | CHAR_01/囚犯初醒态 | expression_bank | 出图/共享/图片/定妆_CHAR_01__囚犯初醒态_表情_克制.png |
| REF_008 | P0 | CHAR_01/囚犯初醒态 | action_pose_pack | 出图/共享/图片/定妆_CHAR_01_囚犯初醒态_action_pose_pack.png |
| REF_015 | P0 | CHAR_02/濒死战损态 | expression_bank | 出图/共享/图片/定妆_CHAR_02__濒死战损态_表情_克制.png |
| REF_016 | P0 | CHAR_02/濒死战损态 | action_pose_pack | 出图/共享/图片/定妆_CHAR_02_濒死战损态_action_pose_pack.png |
| REF_023 | P0 | CHAR_03/诈死复苏态 | expression_bank | 出图/共享/图片/定妆_CHAR_03__诈死复苏态_表情_克制.png |
| REF_024 | P0 | CHAR_03/诈死复苏态 | action_pose_pack | 出图/共享/图片/定妆_CHAR_03_诈死复苏态_action_pose_pack.png |
| REF_047 | P0 | EP02_CLIP01 | regional_construct_plate | 出图/第2集/区域构建/EP02_CLIP01/empty_plate.png |
| REF_048 | P0 | EP02_CLIP01 | region_masks | 出图/第2集/区域构建/EP02_CLIP01/masks.json |
| REF_049 | P0 | EP02_CLIP02 | regional_construct_plate | 出图/第2集/区域构建/EP02_CLIP02/empty_plate.png |
| REF_050 | P0 | EP02_CLIP02 | region_masks | 出图/第2集/区域构建/EP02_CLIP02/masks.json |
| REF_051 | P0 | EP02_CLIP03 | regional_construct_plate | 出图/第2集/区域构建/EP02_CLIP03/empty_plate.png |
| REF_052 | P0 | EP02_CLIP03 | region_masks | 出图/第2集/区域构建/EP02_CLIP03/masks.json |
| REF_053 | P0 | EP02_CLIP04 | regional_construct_plate | 出图/第2集/区域构建/EP02_CLIP04/empty_plate.png |
| REF_054 | P0 | EP02_CLIP04 | region_masks | 出图/第2集/区域构建/EP02_CLIP04/masks.json |
| REF_055 | P0 | EP02_CLIP05 | regional_construct_plate | 出图/第2集/区域构建/EP02_CLIP05/empty_plate.png |
| REF_056 | P0 | EP02_CLIP05 | region_masks | 出图/第2集/区域构建/EP02_CLIP05/masks.json |
| REF_057 | P0 | EP02_CLIP06 | regional_construct_plate | 出图/第2集/区域构建/EP02_CLIP06/empty_plate.png |
| REF_058 | P0 | EP02_CLIP06 | region_masks | 出图/第2集/区域构建/EP02_CLIP06/masks.json |
| REF_059 | P0 | EP02_CLIP07 | regional_construct_plate | 出图/第2集/区域构建/EP02_CLIP07/empty_plate.png |
| REF_060 | P0 | EP02_CLIP07 | region_masks | 出图/第2集/区域构建/EP02_CLIP07/masks.json |
| REF_061 | P0 | EP02_CLIP09 | regional_construct_plate | 出图/第2集/区域构建/EP02_CLIP09/empty_plate.png |
| REF_062 | P0 | EP02_CLIP09 | region_masks | 出图/第2集/区域构建/EP02_CLIP09/masks.json |

## 关键镜候选

| Clip | Tags | N | Status | Best |
|---|---|---:|---|---|
| EP02_CLIP01 | opening、hook_or_payoff、multi_subject、strong_emotion | 6 | selected | candidate_01 |
| EP02_CLIP02 | hook_or_payoff、multi_subject、strong_emotion | 5 | selected | candidate_01 |
| EP02_CLIP03 | multi_subject、strong_emotion、action | 5 | selected | candidate_01 |
| EP02_CLIP04 | signature_scene、hook_or_payoff、multi_subject、strong_emotion、action | 6 | selected | candidate_01 |
| EP02_CLIP05 | hook_or_payoff、multi_subject、strong_emotion | 5 | selected | candidate_01 |
| EP02_CLIP06 | hook_or_payoff、multi_subject、strong_emotion | 5 | selected | candidate_01 |
| EP02_CLIP07 | hook_or_payoff、multi_subject、strong_emotion | 5 | selected | candidate_01 |
| EP02_CLIP08 | hook_or_payoff、multi_subject、strong_emotion、action | 5 | selected | candidate_01 |
| EP02_CLIP09 | multi_subject、strong_emotion | 5 | selected | candidate_01 |
| EP02_CLIP10 | hook_or_payoff、multi_subject、action | 5 | selected | candidate_01 |

## 多人同框分区构建

| Clip | Mode | Manifest | Steps |
|---|---|---|---|
| EP02_CLIP01 | regional_construct_required | 出图/第2集/区域构建/EP02_CLIP01/regional_construct_manifest.json | generate_empty_plate_without_characters → create_region_masks_per_slot → inpaint_each_slot_with_own_reference_group → relighting_color_match → final_qc_identity_slots |
| EP02_CLIP02 | regional_construct_required | 出图/第2集/区域构建/EP02_CLIP02/regional_construct_manifest.json | generate_empty_plate_without_characters → create_region_masks_per_slot → inpaint_each_slot_with_own_reference_group → relighting_color_match → final_qc_identity_slots |
| EP02_CLIP03 | regional_construct_required | 出图/第2集/区域构建/EP02_CLIP03/regional_construct_manifest.json | generate_empty_plate_without_characters → create_region_masks_per_slot → inpaint_each_slot_with_own_reference_group → relighting_color_match → final_qc_identity_slots |
| EP02_CLIP04 | regional_construct_required | 出图/第2集/区域构建/EP02_CLIP04/regional_construct_manifest.json | generate_empty_plate_without_characters → create_region_masks_per_slot → inpaint_each_slot_with_own_reference_group → relighting_color_match → final_qc_identity_slots |
| EP02_CLIP05 | regional_construct_required | 出图/第2集/区域构建/EP02_CLIP05/regional_construct_manifest.json | generate_empty_plate_without_characters → create_region_masks_per_slot → inpaint_each_slot_with_own_reference_group → relighting_color_match → final_qc_identity_slots |
| EP02_CLIP06 | regional_construct_required | 出图/第2集/区域构建/EP02_CLIP06/regional_construct_manifest.json | generate_empty_plate_without_characters → create_region_masks_per_slot → inpaint_each_slot_with_own_reference_group → relighting_color_match → final_qc_identity_slots |
| EP02_CLIP07 | regional_construct_required | 出图/第2集/区域构建/EP02_CLIP07/regional_construct_manifest.json | generate_empty_plate_without_characters → create_region_masks_per_slot → inpaint_each_slot_with_own_reference_group → relighting_color_match → final_qc_identity_slots |
| EP02_CLIP09 | regional_construct_required | 出图/第2集/区域构建/EP02_CLIP09/regional_construct_manifest.json | generate_empty_plate_without_characters → create_region_masks_per_slot → inpaint_each_slot_with_own_reference_group → relighting_color_match → final_qc_identity_slots |
