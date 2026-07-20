# 漫画 Gate — compose — 第9话

- 生成时间：2026-07-20T18:06:47
- 结论：warn
- block/warn/info：0 / 101 / 5

## 记录

- 开发包严格合同: pass
- 源范围/SHA/逐格 coverage 合同: pass
- continuity_audit: chapters=9 block=0 warn=0
- 缩略分镜/name board 审批合同: pass
- 排版审批合同: pass
- 原稿收尾合同: pass
- backend adapter: dreamina_image2image; reference_image_limit=10; persistent_subject=False
- 角色注册表 v2: pass
- 角色多视图技术齐套与人审签收: pass
- chapter_beat_audit: must=0 warn=1（advisory·不阻断）
- setup_payoff_ledger: must=0 warn=0（advisory·不阻断）
- reentry_context_audit: must=0 warn=0（advisory·不阻断）
- entity_presence_audit: must=0 warn=2（advisory·不阻断）
- redundancy_audit: must=0 warn=11（advisory·不阻断）
- subtext_audit: must=0 warn=0（advisory·不阻断）
- reference_planner: 含角色格 48 需处理 27；处方 SHA 已校验
- panel_variety: panels=48 近重复对=0（advisory·不阻断）
- style consistency refreshed: 生产数据/comic_style_consistency_第9话.md
- character consistency refreshed: 生产数据/comic_character_consistency_第9话.md
- scene/prop consistency refreshed: 生产数据/comic_scene_prop_consistency_第9话.md

## Findings

| severity | code | artifact | reason | return_to | suggested_fix |
|---|---|---|---|---|---|
| warn | ending_mode_mismatch | 生产数据/comic_chapter_beat_audit_第9话.json | 合同 ending_mode=closure_with_new_promise，末格 story_function=ending_promise；期望候选为 ['hook', 'new_promise', 'resolution']。这是编辑复核提示，不是硬闸。 | comic-script | 按机检建议回 comic-script 修分话/分格后重跑。 |
| warn | mentioned_not_bound | 生产数据/comic_entity_presence_audit_第9话.json | P030 画面描述提到「王进」（registry 实体 CHAR_WANG_JIN），但该格 characters/references/scene_anchor 都没绑它——出图不会附其定妆参考，形态全靠模型自由发挥。确认入画则补进该格 references（或 characters），不入画则改写描述。 | comic-script | 按机检建议回 comic-script 修分话/分格后重跑。 |
| warn | mentioned_not_bound | 生产数据/comic_entity_presence_audit_第9话.json | P048 画面描述提到「王进」（registry 实体 CHAR_WANG_JIN），但该格 characters/references/scene_anchor 都没绑它——出图不会附其定妆参考，形态全靠模型自由发挥。确认入画则补进该格 references（或 characters），不入画则改写描述。 | comic-script | 按机检建议回 comic-script 修分话/分格后重跑。 |
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
| warn | missing_reference | 生产数据/comic_reference_plan_第9话.json | P021·史进：缺 背身参考（背影/过肩格） | identity | 按处方补该角色缺的视图/表情/服装参考并重建出图包。 |
| warn | missing_reference | 生产数据/comic_reference_plan_第9话.json | P021·李吉：缺 背身参考（背影/过肩格） | identity | 按处方补该角色缺的视图/表情/服装参考并重建出图包。 |
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
| warn | missing_reference | 生产数据/comic_reference_plan_第9话.json | P036·史进：缺 全身/三视图参考（远景/全身动作格·单张头肩定妆不够） | identity | 按处方补该角色缺的视图/表情/服装参考并重建出图包。 |
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
| info | panel_post_qc_warn | 出图/第9话/panels/P034.png | P034 的落盘 post_qc=warn 已人审签收为误报：人工复核确认候选白区为白战袍、白毡帽与山水门洞形成的自然亮区，不是预烘焙气泡或文字容器；画面无文字，人物身份、动作与场景可用。 | review | 若该格重抽或构图变化，需要重新复核 panel_qc。 |
| info | panel_post_qc_warn | 出图/第9话/panels/P043.png | P043 的落盘 post_qc=warn 已人审签收为误报：人工复核确认候选白区为茶坊门帘与门外天光形成的自然亮区，不是预烘焙气泡或文字容器；画面无文字，人物身份、动作与场景可用。 | review | 若该格重抽或构图变化，需要重新复核 panel_qc。 |
| info | panel_post_qc_warn | 出图/第9话/panels/P046.png | P046 的落盘 post_qc=warn 已人审签收为误报：人工复核确认候选白区为茶坊门外天光与浅色帘幕形成的自然亮区，不是预烘焙气泡或文字容器；画面无文字，人物身份、动作与场景可用。 | review | 若该格重抽或构图变化，需要重新复核 panel_qc。 |
| info | panel_post_qc_warn | 出图/第9话/panels/P047.png | P047 的落盘 post_qc=warn 已人审签收为误报：人工复核确认候选白区为茶坊门帘与窗外天空形成的自然亮区，不是预烘焙气泡或文字容器；画面无文字，人物身份、动作与场景可用。 | review | 若该格重抽或构图变化，需要重新复核 panel_qc。 |
| info | panel_post_qc_warn | 出图/第9话/panels/P048.png | P048 的落盘 post_qc=warn 已人审签收为误报：人工复核确认候选白区为茶坊门外天光与浅色帘幕形成的自然亮区，不是预烘焙气泡或文字容器；画面无文字，人物身份、动作与场景可用。 | review | 若该格重抽或构图变化，需要重新复核 panel_qc。 |
| warn | panel_style_outlier | 出图/第9话/panels/P004.png | 风格指纹内聚度 0.6626 明显低于本话中位 0.8292，疑似画风、细节密度或照片感跳变。 | image | 与全话 contact sheet 并排人审；若确实跳变，回 comic-image 用同一风格锚和参考图重抽该格。 |
| warn | panel_style_outlier | 出图/第9话/panels/P005.png | 风格指纹内聚度 0.7122 明显低于本话中位 0.8292，疑似画风、细节密度或照片感跳变。 | image | 与全话 contact sheet 并排人审；若确实跳变，回 comic-image 用同一风格锚和参考图重抽该格。 |
| warn | panel_style_outlier | 出图/第9话/panels/P008.png | 风格指纹内聚度 0.7659 明显低于本话中位 0.8292，疑似画风、细节密度或照片感跳变。 | image | 与全话 contact sheet 并排人审；若确实跳变，回 comic-image 用同一风格锚和参考图重抽该格。 |
| warn | panel_style_outlier | 出图/第9话/panels/P009.png | 风格指纹内聚度 0.7596 明显低于本话中位 0.8292，疑似画风、细节密度或照片感跳变。 | image | 与全话 contact sheet 并排人审；若确实跳变，回 comic-image 用同一风格锚和参考图重抽该格。 |
| warn | panel_style_outlier | 出图/第9话/panels/P010.png | 风格指纹内聚度 0.7605 明显低于本话中位 0.8292，疑似画风、细节密度或照片感跳变。 | image | 与全话 contact sheet 并排人审；若确实跳变，回 comic-image 用同一风格锚和参考图重抽该格。 |
| warn | panel_style_outlier | 出图/第9话/panels/P011.png | 风格指纹内聚度 0.7869 明显低于本话中位 0.8292，疑似画风、细节密度或照片感跳变。 | image | 与全话 contact sheet 并排人审；若确实跳变，回 comic-image 用同一风格锚和参考图重抽该格。 |
| warn | panel_style_outlier | 出图/第9话/panels/P013.png | 风格指纹内聚度 0.7535 明显低于本话中位 0.8292，疑似画风、细节密度或照片感跳变。 | image | 与全话 contact sheet 并排人审；若确实跳变，回 comic-image 用同一风格锚和参考图重抽该格。 |
| warn | panel_style_outlier | 出图/第9话/panels/P015.png | 风格指纹内聚度 0.6771 明显低于本话中位 0.8292，疑似画风、细节密度或照片感跳变。 | image | 与全话 contact sheet 并排人审；若确实跳变，回 comic-image 用同一风格锚和参考图重抽该格。 |
| warn | panel_style_outlier | 出图/第9话/panels/P016.png | 风格指纹内聚度 0.6330 明显低于本话中位 0.8292，疑似画风、细节密度或照片感跳变。 | image | 与全话 contact sheet 并排人审；若确实跳变，回 comic-image 用同一风格锚和参考图重抽该格。 |
| warn | panel_style_outlier | 出图/第9话/panels/P018.png | 风格指纹内聚度 0.7860 明显低于本话中位 0.8292，疑似画风、细节密度或照片感跳变。 | image | 与全话 contact sheet 并排人审；若确实跳变，回 comic-image 用同一风格锚和参考图重抽该格。 |
| warn | panel_style_outlier | 出图/第9话/panels/P021.png | 风格指纹内聚度 0.7455 明显低于本话中位 0.8292，疑似画风、细节密度或照片感跳变。 | image | 与全话 contact sheet 并排人审；若确实跳变，回 comic-image 用同一风格锚和参考图重抽该格。 |
| warn | panel_style_outlier | 出图/第9话/panels/P022.png | 风格指纹内聚度 0.7334 明显低于本话中位 0.8292，疑似画风、细节密度或照片感跳变。 | image | 与全话 contact sheet 并排人审；若确实跳变，回 comic-image 用同一风格锚和参考图重抽该格。 |
| warn | panel_style_outlier | 出图/第9话/panels/P037.png | 风格指纹内聚度 0.7705 明显低于本话中位 0.8292，疑似画风、细节密度或照片感跳变。 | image | 与全话 contact sheet 并排人审；若确实跳变，回 comic-image 用同一风格锚和参考图重抽该格。 |
| warn | panel_style_outlier | 出图/第9话/panels/P039.png | 风格指纹内聚度 0.7575 明显低于本话中位 0.8292，疑似画风、细节密度或照片感跳变。 | image | 与全话 contact sheet 并排人审；若确实跳变，回 comic-image 用同一风格锚和参考图重抽该格。 |
| warn | location_color_grade_shift | 出图/第9话/panels/P009.png | 同场景“LOC_SHI_MANOR”内调色代理偏离组中位：warmth_dev=0.206, tint_dev=0.035。 | image | 人审确认是否为有意光效；否则统一白平衡/冷暖光口径后重抽该格。 |
| warn | location_color_grade_shift | 出图/第9话/panels/P015.png | 同场景“LOC_SHI_MANOR”内调色代理偏离组中位：warmth_dev=0.393, tint_dev=0.005。 | image | 人审确认是否为有意光效；否则统一白平衡/冷暖光口径后重抽该格。 |
| warn | location_color_grade_shift | 出图/第9话/panels/P016.png | 同场景“LOC_SHI_MANOR”内调色代理偏离组中位：warmth_dev=0.210, tint_dev=0.010。 | image | 人审确认是否为有意光效；否则统一白平衡/冷暖光口径后重抽该格。 |
| warn | tone_value_outlier | 出图/第9话/panels/P021.png | 黑白灰量化偏离话内中位：black_ratio=0.3155（中位 0.038），线宽代理 edge_density=0.0962（中位 0.146）。疑似网点密度/黑场/线宽口径不统一。 | image | 对照 finishing_plan 的 tone/black/ink 计划人审；口径确实漂了则统一收尾契约后重抽。 |
| warn | style_anchor_drift | 出图/共享/style_baseline.json | 本话整体指纹与风格锚图最高相似度仅 0.8675，风格锚可能已失去约束力。 | image | 并排比对锚图与本话 contact sheet；必要时更新风格锚或统一重抽。 |
| warn | hair_fingerprint_low | 出图/第9话/panels/P024.png | CHAR_COUNTY_LIEUTENANT hair 指纹与参考图相似度偏低：score=0.359。这是色彩分布代理，需并排人审。 | image | 查看 character consistency contact sheet；如确实换脸/换发型/换服装，回 comic-image 用同一参考组重抽该格。 |
| warn | face_fingerprint_low | 出图/第9话/panels/P021.png | CHAR_LI_JI face 指纹与参考图相似度偏低：score=0.423。这是色彩分布代理，需并排人审。 | image | 查看 character consistency contact sheet；如确实换脸/换发型/换服装，回 comic-image 用同一参考组重抽该格。 |
| warn | hair_fingerprint_low | 出图/第9话/panels/P021.png | CHAR_LI_JI hair 指纹与参考图相似度偏低：score=0.194。这是色彩分布代理，需并排人审。 | image | 查看 character consistency contact sheet；如确实换脸/换发型/换服装，回 comic-image 用同一参考组重抽该格。 |
| warn | hair_fingerprint_low | 出图/第9话/panels/P022.png | CHAR_LI_JI hair 指纹与参考图相似度偏低：score=0.457。这是色彩分布代理，需并排人审。 | image | 查看 character consistency contact sheet；如确实换脸/换发型/换服装，回 comic-image 用同一参考组重抽该格。 |
| warn | face_fingerprint_low | 出图/第9话/panels/P008.png | CHAR_SHI_JIN face 指纹与参考图相似度偏低：score=0.450。这是色彩分布代理，需并排人审。 | image | 查看 character consistency contact sheet；如确实换脸/换发型/换服装，回 comic-image 用同一参考组重抽该格。 |
| warn | hair_fingerprint_low | 出图/第9话/panels/P008.png | CHAR_SHI_JIN hair 指纹与参考图相似度偏低：score=0.207。这是色彩分布代理，需并排人审。 | image | 查看 character consistency contact sheet；如确实换脸/换发型/换服装，回 comic-image 用同一参考组重抽该格。 |
| warn | hair_fingerprint_low | 出图/第9话/panels/P021.png | CHAR_SHI_JIN hair 指纹与参考图相似度偏低：score=0.424。这是色彩分布代理，需并排人审。 | image | 查看 character consistency contact sheet；如确实换脸/换发型/换服装，回 comic-image 用同一参考组重抽该格。 |
| warn | face_fingerprint_low | 出图/第9话/panels/P038.png | CHAR_SHI_JIN face 指纹与参考图相似度偏低：score=0.375。这是色彩分布代理，需并排人审。 | image | 查看 character consistency contact sheet；如确实换脸/换发型/换服装，回 comic-image 用同一参考组重抽该格。 |
| warn | hair_fingerprint_low | 出图/第9话/panels/P038.png | CHAR_SHI_JIN hair 指纹与参考图相似度偏低：score=0.391。这是色彩分布代理，需并排人审。 | image | 查看 character consistency contact sheet；如确实换脸/换发型/换服装，回 comic-image 用同一参考组重抽该格。 |
| warn | face_fingerprint_low | 出图/第9话/panels/P008.png | CHAR_WANG_SI face 指纹与参考图相似度偏低：score=0.411。这是色彩分布代理，需并排人审。 | image | 查看 character consistency contact sheet；如确实换脸/换发型/换服装，回 comic-image 用同一参考组重抽该格。 |
| warn | hair_fingerprint_low | 出图/第9话/panels/P008.png | CHAR_WANG_SI hair 指纹与参考图相似度偏低：score=0.194。这是色彩分布代理，需并排人审。 | image | 查看 character consistency contact sheet；如确实换脸/换发型/换服装，回 comic-image 用同一参考组重抽该格。 |
| warn | hair_fingerprint_low | 出图/第9话/panels/P020.png | CHAR_YANG_CHUN hair 指纹与参考图相似度偏低：score=0.456。这是色彩分布代理，需并排人审。 | image | 查看 character consistency contact sheet；如确实换脸/换发型/换服装，回 comic-image 用同一参考组重抽该格。 |
| warn | hair_fingerprint_low | 出图/第9话/panels/P012.png | CHAR_ZHU_WU hair 指纹与参考图相似度偏低：score=0.429。这是色彩分布代理，需并排人审。 | image | 查看 character consistency contact sheet；如确实换脸/换发型/换服装，回 comic-image 用同一参考组重抽该格。 |
| warn | identity_similarity_engine_degraded | 生产数据/comic_character_consistency_第9话.json | CCIP 动漫身份 embedding 不可用，角色/生物相似度机检降级为色彩分布代理（同色调换脸/变形会漏报）。 | review | 独立 venv 安装 dghs-imgutils 后重跑 gate；在装好前必须以 VLM 并排裁决兜底身份轴。 |
| warn | vlm_judge_unadjudicated | 生产数据/comic_vlm_judge_tasks_第9话.json | VLM 并排判定任务包已生成 137 条但 0 条裁决——角色/生物身份、背景、道具三轴机检空转，画错生物形态这类漂移不会被拦。 | review | 由多模态 agent 逐条看图打分并写回 生产数据/comic_vlm_judge_verdicts_第9话.json 后重跑 gate。 |
