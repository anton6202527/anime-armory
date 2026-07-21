# 漫画 Gate — image_preflight — 第9话

- 生成时间：2026-07-21T05:06:22
- 结论：block
- block/warn/info：2 / 64 / 0

## 记录

- 开发包严格合同: pass
- 源范围/SHA/逐格 coverage 合同: pass
- continuity_audit: chapters=9 block=0 warn=0
- 缩略分镜/name board 审批合同: pass
- 排版审批合同: pass
- 原稿收尾合同: pass
- backend adapter: dreamina_image2image; reference_image_limit=10; persistent_subject=False
- 角色注册表 v2: pass
- chapter_beat_audit: must=0 warn=1（advisory·不阻断）
- setup_payoff_ledger: must=0 warn=0（advisory·不阻断）
- reentry_context_audit: must=0 warn=0（advisory·不阻断）
- entity_presence_audit: must=0 warn=2（advisory·不阻断）
- redundancy_audit: must=0 warn=11（advisory·不阻断）
- subtext_audit: must=0 warn=0（advisory·不阻断）
- reference_planner: 含角色格 48 需处理 27；处方 SHA 已校验

## Findings

| severity | code | artifact | reason | return_to | suggested_fix |
|---|---|---|---|---|---|
| block | model_pack_not_signed_off | 生产数据/comic_model_pack_report.json | 角色多视图技术齐套与人审签收 未通过：6d43dbb3057015c840438c",             "crop_box": []           }         },         {           "view": "three_quarter",           "path": "出图/共享/图片/MON_WHITE_TIGER__three_quarter.png",           "sha256": "93ae3b93a742db5ea825c8937bb3f14be7c1241bcaacc203970986bbe9128d07",           "width": 1086,           "height": 1448,           "source_view": "three_quarter",           "derivation": {             "method": "generated_from_shared_anchor",             "source_path": "出图/共享/图片/MON_WHITE_TIGER__front.png",             "source_sha256": "6a9f73472b8e08376309d41ca79f24051297fbbdfa6d43dbb3057015c840438c",             "crop_box": []           }         },         {           "view": "face",           "path": "出图/共享/图片/MON_WHITE_TIGER__face.png",           "sha256": "3fa67b59c7e736bf7413fbb1997e4c5d52f908f01f4a70c3e397916095502d59",           "width": 1086,           "height": 1448,           "source_view": "face",           "derivation": {             "method": "generated_from_shared_anchor",             "source_path": "出图/共享/图片/MON_WHITE_TIGER__front.png",             "source_sha256": "6a9f73472b8e08376309d41ca79f24051297fbbdfa6d43dbb3057015c840438c",             "crop_box": []           }         }       ],       "model_pack_fingerprint": "5a4cf217537fd9cb86e8b3930115f8336a4b31e9aa127bb0711c340c00ded340",       "signoff": {         "path": "生产数据/comic_model_pack_signoffs/MON_WHITE_TIGER.json",         "status": "current",         "approved_at": "2026-07-16T10:50:03+00:00",         "reviewer": "Codex制作代理"       },       "signoff_required": true,       "readiness": "ready",       "technical_block": false,       "findings": []     }   ],   "summary": {     "assets": 29,     "characters": 27,     "monsters": 2,     "ready": 25,     "needs_approval": 0,     "needs_fix": 4   } } | identity | 按 角色多视图技术齐套与人审签收 输出修复并重新签收后重跑 gate。 |
| block | missing_character_views | 生产数据/comic_identity_report.json | 长线专门定妆未补齐：CHAR_JIN_CUILIAN 缺 front,three_quarter,face；CHAR_JIN_LAO 缺 front,face；CHAR_LI_ZHONG 缺 front,three_quarter,face；CHAR_ZHENG_TU 缺 front,face | identity | 补 front/three_quarter/side/back/face 后重跑 gate。 |
| warn | ending_mode_mismatch | 生产数据/comic_chapter_beat_audit_第9话.json | 合同 ending_mode=closure_with_new_promise，末格 story_function=ending_promise；期望候选为 ['hook', 'new_promise', 'resolution']。这是编辑复核提示，不是硬闸。 | comic-script | 按机检建议回 comic-script 修分话/分格后重跑。 |
| warn | mentioned_not_bound | 生产数据/comic_entity_presence_audit_第9话.json | P030 画面描述提到「王进」（registry 实体 CHAR_WANG_JIN），但该格 characters/references/scene_anchor 都没绑它——出图不会附其定妆参考，形态全靠模型自由发挥。确认入画则补进该格 references（或 characters）；不入画则改写描述，或在该格写 unbound_mention_ack.CHAR_WANG_JIN 签收理由。 | comic-script | 按机检建议回 comic-script 修分话/分格后重跑。 |
| warn | mentioned_not_bound | 生产数据/comic_entity_presence_audit_第9话.json | P048 画面描述提到「王进」（registry 实体 CHAR_WANG_JIN），但该格 characters/references/scene_anchor 都没绑它——出图不会附其定妆参考，形态全靠模型自由发挥。确认入画则补进该格 references（或 characters）；不入画则改写描述，或在该格写 unbound_mention_ack.CHAR_WANG_JIN 签收理由。 | comic-script | 按机检建议回 comic-script 修分话/分格后重跑。 |
| warn | repeated_composition_plan | 生产数据/comic_redundancy_audit_第9话.json | P037、P038、P039、P040 计划了相同的 (场景=LOC_GUANXI_ROAD, 角色=CHAR_SHI_JIN, 景别=特写)——一屏多格时重复构图立刻穿帮；换景别/机位/前景遮挡或合并格。 | comic-script | 按机检建议回 comic-script 修分话/分格后重跑。 |
| warn | repeated_composition_plan | 生产数据/comic_redundancy_audit_第9话.json | P027、P028、P030、P035 计划了相同的 (场景=LOC_SHAOHUA_FORT, 角色=CHAR_CHEN_DA/CHAR_SHI_JIN/CHAR_YANG_CHUN/CHAR_ZHU_WU, 景别=特写)——一屏多格时重复构图立刻穿帮；换景别/机位/前景遮挡或合并格。 | comic-script | 按机检建议回 comic-script 修分话/分格后重跑。 |
| warn | repeated_composition_plan | 生产数据/comic_redundancy_audit_第9话.json | P029、P033、P034 计划了相同的 (场景=LOC_SHAOHUA_FORT, 角色=CHAR_SHI_JIN, 景别=特写)——一屏多格时重复构图立刻穿帮；换景别/机位/前景遮挡或合并格。 | comic-script | 按机检建议回 comic-script 修分话/分格后重跑。 |
| warn | repeated_composition_plan | 生产数据/comic_redundancy_audit_第9话.json | P031、P032 计划了相同的 (场景=LOC_SHAOHUA_FORT, 角色=CHAR_SHI_JIN/CHAR_ZHU_WU, 景别=特写)——一屏多格时重复构图立刻穿帮；换景别/机位/前景遮挡或合并格。 | comic-script | 按机检建议回 comic-script 修分话/分格后重跑。 |
| warn | repeated_composition_plan | 生产数据/comic_redundancy_audit_第9话.json | P001、P002、P009、P012、P020、P025 计划了相同的 (场景=LOC_SHI_MANOR, 角色=CHAR_CHEN_DA/CHAR_SHI_JIN/CHAR_YANG_CHUN/CHAR_ZHU_WU, 景别=特写)——一屏多格时重复构图立刻穿帮；换景别/机位/前景遮挡或合并格。 | comic-script | 按机检建议回 comic-script 修分话/分格后重跑。 |
| warn | repeated_composition_plan | 生产数据/comic_redundancy_audit_第9话.json | P014、P024 计划了相同的 (场景=LOC_SHI_MANOR, 角色=CHAR_COUNTY_LIEUTENANT, 景别=特写)——一屏多格时重复构图立刻穿帮；换景别/机位/前景遮挡或合并格。 | comic-script | 按机检建议回 comic-script 修分话/分格后重跑。 |
| warn | repeated_composition_plan | 生产数据/comic_redundancy_audit_第9话.json | P006、P021、P022 计划了相同的 (场景=LOC_SHI_MANOR, 角色=CHAR_LI_JI/CHAR_SHI_JIN, 景别=特写)——一屏多格时重复构图立刻穿帮；换景别/机位/前景遮挡或合并格。 | comic-script | 按机检建议回 comic-script 修分话/分格后重跑。 |
| warn | repeated_composition_plan | 生产数据/comic_redundancy_audit_第9话.json | P004、P010、P011、P013、P015、P016、P017、P018、P026 计划了相同的 (场景=LOC_SHI_MANOR, 角色=CHAR_SHI_JIN, 景别=特写)——一屏多格时重复构图立刻穿帮；换景别/机位/前景遮挡或合并格。 | comic-script | 按机检建议回 comic-script 修分话/分格后重跑。 |
| warn | repeated_composition_plan | 生产数据/comic_redundancy_audit_第9话.json | P007、P008 计划了相同的 (场景=LOC_SHI_MANOR, 角色=CHAR_SHI_JIN/CHAR_WANG_SI, 景别=特写)——一屏多格时重复构图立刻穿帮；换景别/机位/前景遮挡或合并格。 | comic-script | 按机检建议回 comic-script 修分话/分格后重跑。 |
| warn | repeated_composition_plan | 生产数据/comic_redundancy_audit_第9话.json | P045、P047、P048 计划了相同的 (场景=LOC_WEIZHOU_TEAHOUSE, 角色=CHAR_LU_DA/CHAR_SHI_JIN, 景别=特写)——一屏多格时重复构图立刻穿帮；换景别/机位/前景遮挡或合并格。 | comic-script | 按机检建议回 comic-script 修分话/分格后重跑。 |
| warn | repeated_composition_plan | 生产数据/comic_redundancy_audit_第9话.json | P042、P043、P044 计划了相同的 (场景=LOC_WEIZHOU_TEAHOUSE, 角色=CHAR_SHI_JIN, 景别=特写)——一屏多格时重复构图立刻穿帮；换景别/机位/前景遮挡或合并格。 | comic-script | 按机检建议回 comic-script 修分话/分格后重跑。 |
| warn | same_frame_color_collision | 生产数据/comic_reference_plan_第9话.json | P001 多人同框主色撞色（易串脸）：CHAR_ZHU_WU↔CHAR_CHEN_DA（同主色「红」）——用互斥发色/服装主色/配饰强分，必要时拆反打。 | identity | 按处方补该角色缺的视图/表情/服装参考并重建出图包。 |
| warn | multi_character_closeup | 生产数据/comic_reference_plan_第9话.json | P001 多人近景=串脸最高发档：优先拆单人CU+反打或降景别，坚持同框须登记分区/分别出图+合成。 | identity | 按处方补该角色缺的视图/表情/服装参考并重建出图包。 |
| warn | same_frame_color_collision | 生产数据/comic_reference_plan_第9话.json | P002 多人同框主色撞色（易串脸）：CHAR_ZHU_WU↔CHAR_CHEN_DA（同主色「红」）——用互斥发色/服装主色/配饰强分，必要时拆反打。 | identity | 按处方补该角色缺的视图/表情/服装参考并重建出图包。 |
| warn | multi_character_closeup | 生产数据/comic_reference_plan_第9话.json | P002 多人近景=串脸最高发档：优先拆单人CU+反打或降景别，坚持同框须登记分区/分别出图+合成。 | identity | 按处方补该角色缺的视图/表情/服装参考并重建出图包。 |
| warn | multi_character_closeup | 生产数据/comic_reference_plan_第9话.json | P003 多人近景=串脸最高发档：优先拆单人CU+反打或降景别，坚持同框须登记分区/分别出图+合成。 | identity | 按处方补该角色缺的视图/表情/服装参考并重建出图包。 |
| warn | same_frame_color_collision | 生产数据/comic_reference_plan_第9话.json | P006 多人同框主色撞色（易串脸）：CHAR_SHI_JIN↔CHAR_LI_JI（同主色「黑」）——用互斥发色/服装主色/配饰强分，必要时拆反打。 | identity | 按处方补该角色缺的视图/表情/服装参考并重建出图包。 |
| warn | multi_character_closeup | 生产数据/comic_reference_plan_第9话.json | P006 多人近景=串脸最高发档：优先拆单人CU+反打或降景别，坚持同框须登记分区/分别出图+合成。 | identity | 按处方补该角色缺的视图/表情/服装参考并重建出图包。 |
| warn | missing_reference | 生产数据/comic_reference_plan_第9话.json | P007·王四：缺 45°/three_quarter 参考（档位或本格变化量需要） | identity | 按处方补该角色缺的视图/表情/服装参考并重建出图包。 |
| warn | multi_character_closeup | 生产数据/comic_reference_plan_第9话.json | P007 多人近景=串脸最高发档：优先拆单人CU+反打或降景别，坚持同框须登记分区/分别出图+合成。 | identity | 按处方补该角色缺的视图/表情/服装参考并重建出图包。 |
| warn | missing_reference | 生产数据/comic_reference_plan_第9话.json | P008·王四：缺 45°/three_quarter 参考（档位或本格变化量需要） | identity | 按处方补该角色缺的视图/表情/服装参考并重建出图包。 |
| warn | multi_character_closeup | 生产数据/comic_reference_plan_第9话.json | P008 多人近景=串脸最高发档：优先拆单人CU+反打或降景别，坚持同框须登记分区/分别出图+合成。 | identity | 按处方补该角色缺的视图/表情/服装参考并重建出图包。 |
| warn | same_frame_color_collision | 生产数据/comic_reference_plan_第9话.json | P009 多人同框主色撞色（易串脸）：CHAR_ZHU_WU↔CHAR_CHEN_DA（同主色「红」）——用互斥发色/服装主色/配饰强分，必要时拆反打。 | identity | 按处方补该角色缺的视图/表情/服装参考并重建出图包。 |
| warn | multi_character_closeup | 生产数据/comic_reference_plan_第9话.json | P009 多人近景=串脸最高发档：优先拆单人CU+反打或降景别，坚持同框须登记分区/分别出图+合成。 | identity | 按处方补该角色缺的视图/表情/服装参考并重建出图包。 |
| warn | same_frame_color_collision | 生产数据/comic_reference_plan_第9话.json | P012 多人同框主色撞色（易串脸）：CHAR_ZHU_WU↔CHAR_CHEN_DA（同主色「红」）——用互斥发色/服装主色/配饰强分，必要时拆反打。 | identity | 按处方补该角色缺的视图/表情/服装参考并重建出图包。 |
| warn | multi_character_closeup | 生产数据/comic_reference_plan_第9话.json | P012 多人近景=串脸最高发档：优先拆单人CU+反打或降景别，坚持同框须登记分区/分别出图+合成。 | identity | 按处方补该角色缺的视图/表情/服装参考并重建出图包。 |
| warn | missing_reference | 生产数据/comic_reference_plan_第9话.json | P014·华阴县尉：缺 45°/three_quarter 参考（档位或本格变化量需要） | identity | 按处方补该角色缺的视图/表情/服装参考并重建出图包。 |
| warn | same_frame_color_collision | 生产数据/comic_reference_plan_第9话.json | P019 多人同框主色撞色（易串脸）：CHAR_ZHU_WU↔CHAR_CHEN_DA（同主色「红」）——用互斥发色/服装主色/配饰强分，必要时拆反打。 | identity | 按处方补该角色缺的视图/表情/服装参考并重建出图包。 |
| warn | multi_character_closeup | 生产数据/comic_reference_plan_第9话.json | P019 多人近景=串脸最高发档：优先拆单人CU+反打或降景别，坚持同框须登记分区/分别出图+合成。 | identity | 按处方补该角色缺的视图/表情/服装参考并重建出图包。 |
| warn | same_frame_color_collision | 生产数据/comic_reference_plan_第9话.json | P020 多人同框主色撞色（易串脸）：CHAR_ZHU_WU↔CHAR_CHEN_DA（同主色「红」）——用互斥发色/服装主色/配饰强分，必要时拆反打。 | identity | 按处方补该角色缺的视图/表情/服装参考并重建出图包。 |
| warn | multi_character_closeup | 生产数据/comic_reference_plan_第9话.json | P020 多人近景=串脸最高发档：优先拆单人CU+反打或降景别，坚持同框须登记分区/分别出图+合成。 | identity | 按处方补该角色缺的视图/表情/服装参考并重建出图包。 |
| warn | same_frame_color_collision | 生产数据/comic_reference_plan_第9话.json | P021 多人同框主色撞色（易串脸）：CHAR_SHI_JIN↔CHAR_LI_JI（同主色「黑」）——用互斥发色/服装主色/配饰强分，必要时拆反打。 | identity | 按处方补该角色缺的视图/表情/服装参考并重建出图包。 |
| warn | multi_character_closeup | 生产数据/comic_reference_plan_第9话.json | P021 多人近景=串脸最高发档：优先拆单人CU+反打或降景别，坚持同框须登记分区/分别出图+合成。 | identity | 按处方补该角色缺的视图/表情/服装参考并重建出图包。 |
| warn | same_frame_color_collision | 生产数据/comic_reference_plan_第9话.json | P022 多人同框主色撞色（易串脸）：CHAR_SHI_JIN↔CHAR_LI_JI（同主色「黑」）——用互斥发色/服装主色/配饰强分，必要时拆反打。 | identity | 按处方补该角色缺的视图/表情/服装参考并重建出图包。 |
| warn | multi_character_closeup | 生产数据/comic_reference_plan_第9话.json | P022 多人近景=串脸最高发档：优先拆单人CU+反打或降景别，坚持同框须登记分区/分别出图+合成。 | identity | 按处方补该角色缺的视图/表情/服装参考并重建出图包。 |
| warn | multi_character_closeup | 生产数据/comic_reference_plan_第9话.json | P023 多人近景=串脸最高发档：优先拆单人CU+反打或降景别，坚持同框须登记分区/分别出图+合成。 | identity | 按处方补该角色缺的视图/表情/服装参考并重建出图包。 |
| warn | missing_reference | 生产数据/comic_reference_plan_第9话.json | P024·华阴县尉：缺 45°/three_quarter 参考（档位或本格变化量需要） | identity | 按处方补该角色缺的视图/表情/服装参考并重建出图包。 |
| warn | same_frame_color_collision | 生产数据/comic_reference_plan_第9话.json | P025 多人同框主色撞色（易串脸）：CHAR_ZHU_WU↔CHAR_CHEN_DA（同主色「红」）——用互斥发色/服装主色/配饰强分，必要时拆反打。 | identity | 按处方补该角色缺的视图/表情/服装参考并重建出图包。 |
| warn | multi_character_closeup | 生产数据/comic_reference_plan_第9话.json | P025 多人近景=串脸最高发档：优先拆单人CU+反打或降景别，坚持同框须登记分区/分别出图+合成。 | identity | 按处方补该角色缺的视图/表情/服装参考并重建出图包。 |
| warn | same_frame_color_collision | 生产数据/comic_reference_plan_第9话.json | P027 多人同框主色撞色（易串脸）：CHAR_ZHU_WU↔CHAR_CHEN_DA（同主色「红」）——用互斥发色/服装主色/配饰强分，必要时拆反打。 | identity | 按处方补该角色缺的视图/表情/服装参考并重建出图包。 |
| warn | multi_character_closeup | 生产数据/comic_reference_plan_第9话.json | P027 多人近景=串脸最高发档：优先拆单人CU+反打或降景别，坚持同框须登记分区/分别出图+合成。 | identity | 按处方补该角色缺的视图/表情/服装参考并重建出图包。 |
| warn | same_frame_color_collision | 生产数据/comic_reference_plan_第9话.json | P028 多人同框主色撞色（易串脸）：CHAR_ZHU_WU↔CHAR_CHEN_DA（同主色「红」）——用互斥发色/服装主色/配饰强分，必要时拆反打。 | identity | 按处方补该角色缺的视图/表情/服装参考并重建出图包。 |
| warn | multi_character_closeup | 生产数据/comic_reference_plan_第9话.json | P028 多人近景=串脸最高发档：优先拆单人CU+反打或降景别，坚持同框须登记分区/分别出图+合成。 | identity | 按处方补该角色缺的视图/表情/服装参考并重建出图包。 |
| warn | same_frame_color_collision | 生产数据/comic_reference_plan_第9话.json | P030 多人同框主色撞色（易串脸）：CHAR_ZHU_WU↔CHAR_CHEN_DA（同主色「红」）——用互斥发色/服装主色/配饰强分，必要时拆反打。 | identity | 按处方补该角色缺的视图/表情/服装参考并重建出图包。 |
| warn | multi_character_closeup | 生产数据/comic_reference_plan_第9话.json | P030 多人近景=串脸最高发档：优先拆单人CU+反打或降景别，坚持同框须登记分区/分别出图+合成。 | identity | 按处方补该角色缺的视图/表情/服装参考并重建出图包。 |
| warn | multi_character_closeup | 生产数据/comic_reference_plan_第9话.json | P031 多人近景=串脸最高发档：优先拆单人CU+反打或降景别，坚持同框须登记分区/分别出图+合成。 | identity | 按处方补该角色缺的视图/表情/服装参考并重建出图包。 |
| warn | multi_character_closeup | 生产数据/comic_reference_plan_第9话.json | P032 多人近景=串脸最高发档：优先拆单人CU+反打或降景别，坚持同框须登记分区/分别出图+合成。 | identity | 按处方补该角色缺的视图/表情/服装参考并重建出图包。 |
| warn | same_frame_color_collision | 生产数据/comic_reference_plan_第9话.json | P035 多人同框主色撞色（易串脸）：CHAR_ZHU_WU↔CHAR_CHEN_DA（同主色「红」）——用互斥发色/服装主色/配饰强分，必要时拆反打。 | identity | 按处方补该角色缺的视图/表情/服装参考并重建出图包。 |
| warn | multi_character_closeup | 生产数据/comic_reference_plan_第9话.json | P035 多人近景=串脸最高发档：优先拆单人CU+反打或降景别，坚持同框须登记分区/分别出图+合成。 | identity | 按处方补该角色缺的视图/表情/服装参考并重建出图包。 |
| warn | missing_reference | 生产数据/comic_reference_plan_第9话.json | P036·朱武：缺 全身/三视图参考（远景/全身动作格·单张头肩定妆不够） | identity | 按处方补该角色缺的视图/表情/服装参考并重建出图包。 |
| warn | missing_reference | 生产数据/comic_reference_plan_第9话.json | P036·陈达：缺 全身/三视图参考（远景/全身动作格·单张头肩定妆不够） | identity | 按处方补该角色缺的视图/表情/服装参考并重建出图包。 |
| warn | missing_reference | 生产数据/comic_reference_plan_第9话.json | P036·杨春：缺 全身/三视图参考（远景/全身动作格·单张头肩定妆不够） | identity | 按处方补该角色缺的视图/表情/服装参考并重建出图包。 |
| warn | same_frame_color_collision | 生产数据/comic_reference_plan_第9话.json | P036 多人同框主色撞色（易串脸）：CHAR_ZHU_WU↔CHAR_CHEN_DA（同主色「红」）——用互斥发色/服装主色/配饰强分，必要时拆反打。 | identity | 按处方补该角色缺的视图/表情/服装参考并重建出图包。 |
| warn | multi_character_closeup | 生产数据/comic_reference_plan_第9话.json | P036 多人近景=串脸最高发档：优先拆单人CU+反打或降景别，坚持同框须登记分区/分别出图+合成。 | identity | 按处方补该角色缺的视图/表情/服装参考并重建出图包。 |
| warn | same_frame_color_collision | 生产数据/comic_reference_plan_第9话.json | P045 多人同框主色撞色（易串脸）：CHAR_LU_DA↔CHAR_SHI_JIN（同主色「黑」）——用互斥发色/服装主色/配饰强分，必要时拆反打。 | identity | 按处方补该角色缺的视图/表情/服装参考并重建出图包。 |
| warn | multi_character_closeup | 生产数据/comic_reference_plan_第9话.json | P045 多人近景=串脸最高发档：优先拆单人CU+反打或降景别，坚持同框须登记分区/分别出图+合成。 | identity | 按处方补该角色缺的视图/表情/服装参考并重建出图包。 |
| warn | missing_reference | 生产数据/comic_reference_plan_第9话.json | P046·鲁达：缺 全身/三视图参考（远景/全身动作格·单张头肩定妆不够） | identity | 按处方补该角色缺的视图/表情/服装参考并重建出图包。 |
| warn | same_frame_color_collision | 生产数据/comic_reference_plan_第9话.json | P047 多人同框主色撞色（易串脸）：CHAR_LU_DA↔CHAR_SHI_JIN（同主色「黑」）——用互斥发色/服装主色/配饰强分，必要时拆反打。 | identity | 按处方补该角色缺的视图/表情/服装参考并重建出图包。 |
| warn | multi_character_closeup | 生产数据/comic_reference_plan_第9话.json | P047 多人近景=串脸最高发档：优先拆单人CU+反打或降景别，坚持同框须登记分区/分别出图+合成。 | identity | 按处方补该角色缺的视图/表情/服装参考并重建出图包。 |
| warn | same_frame_color_collision | 生产数据/comic_reference_plan_第9话.json | P048 多人同框主色撞色（易串脸）：CHAR_LU_DA↔CHAR_SHI_JIN（同主色「黑」）——用互斥发色/服装主色/配饰强分，必要时拆反打。 | identity | 按处方补该角色缺的视图/表情/服装参考并重建出图包。 |
| warn | multi_character_closeup | 生产数据/comic_reference_plan_第9话.json | P048 多人近景=串脸最高发档：优先拆单人CU+反打或降景别，坚持同框须登记分区/分别出图+合成。 | identity | 按处方补该角色缺的视图/表情/服装参考并重建出图包。 |
