# 无成本图片生产包

- episode: 第1集
- reference_generation_tasks: 26
- keyshot_candidate_tasks: 7
- regional_construct_manifests: 4
- shot_packages: 7

## P0 参考资产补图

| Task | Priority | Owner | Slot | Output |
|---|---|---|---|---|
| REF_007 | P0 | CHAR_HE_PINGSHENG/常态 | expression_bank | 出图/共享/图片/定妆_贺平生_表情_克制.png |
| REF_008 | P0 | CHAR_HE_PINGSHENG/常态 | action_pose_pack | 出图/共享/图片/定妆_CHAR_HE_PINGSHENG_常态_action_pose_pack.png |
| REF_015 | P0 | CHAR_HE_PINGSHENG/幼年 | expression_bank | 出图/共享/图片/定妆_贺平生_幼年_表情_克制.png |
| REF_016 | P0 | CHAR_HE_PINGSHENG/幼年 | action_pose_pack | 出图/共享/图片/定妆_CHAR_HE_PINGSHENG_幼年_action_pose_pack.png |
| REF_023 | P0 | CHAR_ZHANG_LAODA/常态 | expression_bank | 出图/共享/图片/定妆_CHAR_ZHANG_LAODA_常态_expression_bank.png |
| REF_024 | P0 | CHAR_ZHANG_LAODA/常态 | action_pose_pack | 出图/共享/图片/定妆_CHAR_ZHANG_LAODA_常态_action_pose_pack.png |
| REF_031 | P0 | CHAR_HAN_LAOSAN/常态 | expression_bank | 出图/共享/图片/定妆_CHAR_HAN_LAOSAN_常态_expression_bank.png |
| REF_032 | P0 | CHAR_HAN_LAOSAN/常态 | action_pose_pack | 出图/共享/图片/定妆_CHAR_HAN_LAOSAN_常态_action_pose_pack.png |
| REF_039 | P0 | CHAR_JIANG_JIAN/背影 | expression_bank | 出图/共享/图片/定妆_CHAR_JIANG_JIAN_背影_expression_bank.png |
| REF_040 | P0 | CHAR_JIANG_JIAN/背影 | action_pose_pack | 出图/共享/图片/定妆_CHAR_JIANG_JIAN_背影_action_pose_pack.png |
| REF_047 | P0 | CHAR_TAIXUMEN_ZHANGLAO/回忆背影 | expression_bank | 出图/共享/图片/定妆_CHAR_TAIXUMEN_ZHANGLAO_回忆背影_expression_bank.png |
| REF_048 | P0 | CHAR_TAIXUMEN_ZHANGLAO/回忆背影 | action_pose_pack | 出图/共享/图片/定妆_CHAR_TAIXUMEN_ZHANGLAO_回忆背影_action_pose_pack.png |
| REF_055 | P0 | CHAR_HE_SANJIE/回忆影 | expression_bank | 出图/共享/图片/定妆_CHAR_HE_SANJIE_回忆影_expression_bank.png |
| REF_056 | P0 | CHAR_HE_SANJIE/回忆影 | action_pose_pack | 出图/共享/图片/定妆_CHAR_HE_SANJIE_回忆影_action_pose_pack.png |
| REF_063 | P0 | CROWD_ZAYI/虚化 | expression_bank | 出图/共享/图片/定妆_CROWD_ZAYI_虚化_expression_bank.png |
| REF_064 | P0 | CROWD_ZAYI/虚化 | action_pose_pack | 出图/共享/图片/定妆_CROWD_ZAYI_虚化_action_pose_pack.png |
| REF_071 | P0 | CROWD_TAIXU_CULTIVATOR/远景剪影 | expression_bank | 出图/共享/图片/定妆_CROWD_TAIXU_CULTIVATOR_远景剪影_expression_bank.png |
| REF_072 | P0 | CROWD_TAIXU_CULTIVATOR/远景剪影 | action_pose_pack | 出图/共享/图片/定妆_CROWD_TAIXU_CULTIVATOR_远景剪影_action_pose_pack.png |
| REF_105 | P0 | EP01_CLIP01 | regional_construct_plate | 出图/第1集/区域构建/EP01_CLIP01/empty_plate.png |
| REF_106 | P0 | EP01_CLIP01 | region_masks | 出图/第1集/区域构建/EP01_CLIP01/masks.json |
| REF_107 | P0 | EP01_CLIP02 | regional_construct_plate | 出图/第1集/区域构建/EP01_CLIP02/empty_plate.png |
| REF_108 | P0 | EP01_CLIP02 | region_masks | 出图/第1集/区域构建/EP01_CLIP02/masks.json |
| REF_109 | P0 | EP01_CLIP03 | regional_construct_plate | 出图/第1集/区域构建/EP01_CLIP03/empty_plate.png |
| REF_110 | P0 | EP01_CLIP03 | region_masks | 出图/第1集/区域构建/EP01_CLIP03/masks.json |
| REF_111 | P0 | EP01_CLIP04 | regional_construct_plate | 出图/第1集/区域构建/EP01_CLIP04/empty_plate.png |
| REF_112 | P0 | EP01_CLIP04 | region_masks | 出图/第1集/区域构建/EP01_CLIP04/masks.json |

## 关键镜候选

| Clip | Tags | N | Status | Best |
|---|---|---:|---|---|
| EP01_CLIP01 | opening、hook_or_payoff、multi_subject、strong_emotion | 6 | needs_generation | - |
| EP01_CLIP02 | hook_or_payoff、multi_subject、strong_emotion | 5 | needs_generation | - |
| EP01_CLIP03 | multi_subject、strong_emotion | 5 | needs_generation | - |
| EP01_CLIP04 | multi_subject、strong_emotion | 5 | needs_generation | - |
| EP01_CLIP05 | multi_subject、strong_emotion | 5 | needs_generation | - |
| EP01_CLIP06 | multi_subject、strong_emotion | 5 | needs_generation | - |
| EP01_CLIP07 | multi_subject、strong_emotion | 5 | needs_generation | - |

## 多人同框分区构建

| Clip | Mode | Manifest | Steps |
|---|---|---|---|
| EP01_CLIP01 | regional_construct_required | 出图/第1集/区域构建/EP01_CLIP01/regional_construct_manifest.json | generate_empty_plate_without_characters → create_region_masks_per_slot → inpaint_each_slot_with_own_reference_group → relighting_color_match → final_qc_identity_slots |
| EP01_CLIP02 | regional_construct_required | 出图/第1集/区域构建/EP01_CLIP02/regional_construct_manifest.json | generate_empty_plate_without_characters → create_region_masks_per_slot → inpaint_each_slot_with_own_reference_group → relighting_color_match → final_qc_identity_slots |
| EP01_CLIP03 | regional_construct_required | 出图/第1集/区域构建/EP01_CLIP03/regional_construct_manifest.json | generate_empty_plate_without_characters → create_region_masks_per_slot → inpaint_each_slot_with_own_reference_group → relighting_color_match → final_qc_identity_slots |
| EP01_CLIP04 | regional_construct_required | 出图/第1集/区域构建/EP01_CLIP04/regional_construct_manifest.json | generate_empty_plate_without_characters → create_region_masks_per_slot → inpaint_each_slot_with_own_reference_group → relighting_color_match → final_qc_identity_slots |
