# 漫画 Gate — image_preflight — 第1话

- 生成时间：2026-07-21T22:10:31
- 结论：warn
- block/warn/info：0 / 38 / 4

## 记录

- 开发包严格合同: pass
- 源范围/SHA/逐格 coverage 合同: pass
- continuity_audit: chapters=1 block=0 warn=0
- 缩略分镜/name board 审批合同: pass
- 排版审批合同: pass
- 原稿收尾合同: pass
- backend adapter: openai_gpt_image_project_memory; reference_image_limit=16; persistent_subject=False
- 角色注册表 v2: pass
- 角色多视图技术齐套与人审签收: pass
- chapter_beat_audit: must=0 warn=1（advisory·不阻断）
- setup_payoff_ledger: must=0 warn=0（advisory·不阻断）
- reentry_context_audit: must=0 warn=0（advisory·不阻断）
- entity_presence_audit: must=0 warn=0（advisory·不阻断）
- redundancy_audit: must=0 warn=1（advisory·不阻断）
- subtext_audit: must=0 warn=0（advisory·不阻断）
- reference_planner: 含角色格 16 需处理 15；处方 SHA 已校验

## Findings

| severity | code | artifact | reason | return_to | suggested_fix |
|---|---|---|---|---|---|
| warn | panel_character_integrity_weak | 脚本/第1话/panel_script.json#P001 | P001 的人物完整性契约太泛，未同时覆盖脸/眼/发和手脚/身体/关键道具。 | script | 补脸型、眼型/眼距、发际线、发型、服装标志，以及手脚/身体/道具/接触点完整性。 |
| warn | panel_character_integrity_weak | 脚本/第1话/panel_script.json#P006 | P006 的人物完整性契约太泛，未同时覆盖脸/眼/发和手脚/身体/关键道具。 | script | 补脸型、眼型/眼距、发际线、发型、服装标志，以及手脚/身体/道具/接触点完整性。 |
| warn | panel_character_integrity_weak | 脚本/第1话/panel_script.json#P008 | P008 的人物完整性契约太泛，未同时覆盖脸/眼/发和手脚/身体/关键道具。 | script | 补脸型、眼型/眼距、发际线、发型、服装标志，以及手脚/身体/道具/接触点完整性。 |
| warn | panel_character_integrity_weak | 脚本/第1话/panel_script.json#P009 | P009 的人物完整性契约太泛，未同时覆盖脸/眼/发和手脚/身体/关键道具。 | script | 补脸型、眼型/眼距、发际线、发型、服装标志，以及手脚/身体/道具/接触点完整性。 |
| warn | panel_character_integrity_weak | 脚本/第1话/panel_script.json#P011 | P011 的人物完整性契约太泛，未同时覆盖脸/眼/发和手脚/身体/关键道具。 | script | 补脸型、眼型/眼距、发际线、发型、服装标志，以及手脚/身体/道具/接触点完整性。 |
| warn | panel_character_integrity_weak | 脚本/第1话/panel_script.json#P012 | P012 的人物完整性契约太泛，未同时覆盖脸/眼/发和手脚/身体/关键道具。 | script | 补脸型、眼型/眼距、发际线、发型、服装标志，以及手脚/身体/道具/接触点完整性。 |
| warn | panel_character_integrity_weak | 脚本/第1话/panel_script.json#P013 | P013 的人物完整性契约太泛，未同时覆盖脸/眼/发和手脚/身体/关键道具。 | script | 补脸型、眼型/眼距、发际线、发型、服装标志，以及手脚/身体/道具/接触点完整性。 |
| warn | panel_character_integrity_weak | 脚本/第1话/panel_script.json#P014 | P014 的人物完整性契约太泛，未同时覆盖脸/眼/发和手脚/身体/关键道具。 | script | 补脸型、眼型/眼距、发际线、发型、服装标志，以及手脚/身体/道具/接触点完整性。 |
| warn | panel_character_integrity_weak | 脚本/第1话/panel_script.json#P015 | P015 的人物完整性契约太泛，未同时覆盖脸/眼/发和手脚/身体/关键道具。 | script | 补脸型、眼型/眼距、发际线、发型、服装标志，以及手脚/身体/道具/接触点完整性。 |
| warn | panel_character_integrity_weak | 脚本/第1话/panel_script.json#P016 | P016 的人物完整性契约太泛，未同时覆盖脸/眼/发和手脚/身体/关键道具。 | script | 补脸型、眼型/眼距、发际线、发型、服装标志，以及手脚/身体/道具/接触点完整性。 |
| warn | ending_mode_mismatch | 生产数据/comic_chapter_beat_audit_第1话.json | 合同 ending_mode=complete_closure，末格 story_function=epilogue；期望候选为 ['closure', 'complete_closure', 'payoff', 'resolution']。这是编辑复核提示，不是硬闸。 | comic-script | 按机检建议回 comic-script 修分话/分格后重跑。 |
| info | climax_at_tail | 生产数据/comic_chapter_beat_audit_第1话.json | 高潮候选在 93%；确认中段是否有足够支撑。 | comic-script | 按机检建议回 comic-script 修分话/分格后重跑。 |
| info | payoff_due_here | 生产数据/comic_setup_payoff_audit_第1话.json | 伏笔「首屏异鬼铺皮执笔，读者先知危险而王生不知。」计划本话（第1话）兑现——确认本话已把它收掉并标 status=done。 | comic-script | 按机检建议回 comic-script 修分话/分格后重跑。 |
| info | payoff_due_here | 生产数据/comic_setup_payoff_audit_第1话.json | 伏笔「道士见王生邪气萦绕，王生仍以为求财魔法。」计划本话（第1话）兑现——确认本话已把它收掉并标 status=done。 | comic-script | 按机检建议回 comic-script 修分话/分格后重跑。 |
| info | payoff_due_here | 生产数据/comic_setup_payoff_audit_第1话.json | 伏笔「疯乞让陈氏吞下的浓痰停在胸间。」计划本话（第1话）兑现——确认本话已把它收掉并标 status=done。 | comic-script | 按机检建议回 comic-script 修分话/分格后重跑。 |
| warn | repeated_composition_plan | 生产数据/comic_redundancy_audit_第1话.json | P013、P016 计划了相同的 (场景=LOC_WANG_COURTYARD, 角色=CHAR_CHEN/CHAR_WANG, 景别=近景)——一屏多格时重复构图立刻穿帮；换景别/机位/前景遮挡或合并格。 | comic-script | 按机检建议回 comic-script 修分话/分格后重跑。 |
| warn | same_frame_color_collision | 生产数据/comic_reference_plan_第1话.json | P003 多人同框主色撞色（易串脸）：CHAR_WANG↔CHAR_CHEN（同主色「白」）——用互斥发色/服装主色/配饰强分，必要时拆反打。 | identity | 按处方补该角色缺的视图/表情/服装参考并重建出图包。 |
| warn | same_frame_color_collision | 生产数据/comic_reference_plan_第1话.json | P004 多人同框主色撞色（易串脸）：CHAR_WANG↔CHAR_DAOIST（同主色「白」）——用互斥发色/服装主色/配饰强分，必要时拆反打。 | identity | 按处方补该角色缺的视图/表情/服装参考并重建出图包。 |
| warn | same_frame_color_collision | 生产数据/comic_reference_plan_第1话.json | P006 多人同框主色撞色（易串脸）：CHAR_WANG↔CHAR_DAOIST（同主色「白」）——用互斥发色/服装主色/配饰强分，必要时拆反打。 | identity | 按处方补该角色缺的视图/表情/服装参考并重建出图包。 |
| warn | missing_reference | 生产数据/comic_reference_plan_第1话.json | P007·王生：缺 45°/three_quarter 参考（档位或本格变化量需要） | identity | 按处方补该角色缺的视图/表情/服装参考并重建出图包。 |
| warn | missing_reference | 生产数据/comic_reference_plan_第1话.json | P007·王生：缺 45°/¾ 侧脸参考（动作格主身份锚·避免 frontal 摆拍偏置） | identity | 按处方补该角色缺的视图/表情/服装参考并重建出图包。 |
| warn | missing_reference | 生产数据/comic_reference_plan_第1话.json | P007·画皮鬼：缺 45°/three_quarter 参考（档位或本格变化量需要） | identity | 按处方补该角色缺的视图/表情/服装参考并重建出图包。 |
| warn | missing_reference | 生产数据/comic_reference_plan_第1话.json | P007·画皮鬼：缺 45°/¾ 侧脸参考（动作格主身份锚·避免 frontal 摆拍偏置） | identity | 按处方补该角色缺的视图/表情/服装参考并重建出图包。 |
| warn | same_frame_color_collision | 生产数据/comic_reference_plan_第1话.json | P008 多人同框主色撞色（易串脸）：CHAR_CHEN↔CHAR_WANG（同主色「白」）——用互斥发色/服装主色/配饰强分，必要时拆反打。 | identity | 按处方补该角色缺的视图/表情/服装参考并重建出图包。 |
| warn | missing_reference | 生产数据/comic_reference_plan_第1话.json | P009·道士：缺 45°/three_quarter 参考（档位或本格变化量需要） | identity | 按处方补该角色缺的视图/表情/服装参考并重建出图包。 |
| warn | missing_reference | 生产数据/comic_reference_plan_第1话.json | P009·道士：缺 45°/¾ 侧脸参考（动作格主身份锚·避免 frontal 摆拍偏置） | identity | 按处方补该角色缺的视图/表情/服装参考并重建出图包。 |
| warn | missing_reference | 生产数据/comic_reference_plan_第1话.json | P009·画皮鬼：缺 45°/three_quarter 参考（档位或本格变化量需要） | identity | 按处方补该角色缺的视图/表情/服装参考并重建出图包。 |
| warn | missing_reference | 生产数据/comic_reference_plan_第1话.json | P009·画皮鬼：缺 45°/¾ 侧脸参考（动作格主身份锚·避免 frontal 摆拍偏置） | identity | 按处方补该角色缺的视图/表情/服装参考并重建出图包。 |
| warn | same_frame_color_collision | 生产数据/comic_reference_plan_第1话.json | P010 多人同框主色撞色（易串脸）：CHAR_CHEN↔CHAR_DAOIST（同主色「白」）——用互斥发色/服装主色/配饰强分，必要时拆反打。 | identity | 按处方补该角色缺的视图/表情/服装参考并重建出图包。 |
| warn | same_frame_color_collision | 生产数据/comic_reference_plan_第1话.json | P012 多人同框主色撞色（易串脸）：CHAR_CHEN↔CHAR_WANG（同主色「白」）——用互斥发色/服装主色/配饰强分，必要时拆反打。 | identity | 按处方补该角色缺的视图/表情/服装参考并重建出图包。 |
| warn | missing_reference | 生产数据/comic_reference_plan_第1话.json | P013·陈氏：缺 45°/three_quarter 参考（档位或本格变化量需要） | identity | 按处方补该角色缺的视图/表情/服装参考并重建出图包。 |
| warn | missing_reference | 生产数据/comic_reference_plan_第1话.json | P013·王生：缺 45°/three_quarter 参考（档位或本格变化量需要） | identity | 按处方补该角色缺的视图/表情/服装参考并重建出图包。 |
| warn | same_frame_color_collision | 生产数据/comic_reference_plan_第1话.json | P013 多人同框主色撞色（易串脸）：CHAR_CHEN↔CHAR_WANG（同主色「白」）——用互斥发色/服装主色/配饰强分，必要时拆反打。 | identity | 按处方补该角色缺的视图/表情/服装参考并重建出图包。 |
| warn | multi_character_closeup | 生产数据/comic_reference_plan_第1话.json | P013 多人近景=串脸最高发档：优先拆单人CU+反打或降景别，坚持同框须登记分区/分别出图+合成。 | identity | 按处方补该角色缺的视图/表情/服装参考并重建出图包。 |
| warn | same_frame_color_collision | 生产数据/comic_reference_plan_第1话.json | P014 多人同框主色撞色（易串脸）：CHAR_CHEN↔CHAR_WANG（同主色「白」）——用互斥发色/服装主色/配饰强分，必要时拆反打。 | identity | 按处方补该角色缺的视图/表情/服装参考并重建出图包。 |
| warn | same_frame_color_collision | 生产数据/comic_reference_plan_第1话.json | P015 多人同框主色撞色（易串脸）：CHAR_CHEN↔CHAR_WANG（同主色「白」）——用互斥发色/服装主色/配饰强分，必要时拆反打。 | identity | 按处方补该角色缺的视图/表情/服装参考并重建出图包。 |
| warn | missing_reference | 生产数据/comic_reference_plan_第1话.json | P016·王生：缺 45°/three_quarter 参考（档位或本格变化量需要） | identity | 按处方补该角色缺的视图/表情/服装参考并重建出图包。 |
| warn | missing_reference | 生产数据/comic_reference_plan_第1话.json | P016·王生：缺 背身参考（背影/过肩格） | identity | 按处方补该角色缺的视图/表情/服装参考并重建出图包。 |
| warn | missing_reference | 生产数据/comic_reference_plan_第1话.json | P016·陈氏：缺 45°/three_quarter 参考（档位或本格变化量需要） | identity | 按处方补该角色缺的视图/表情/服装参考并重建出图包。 |
| warn | missing_reference | 生产数据/comic_reference_plan_第1话.json | P016·陈氏：缺 背身参考（背影/过肩格） | identity | 按处方补该角色缺的视图/表情/服装参考并重建出图包。 |
| warn | same_frame_color_collision | 生产数据/comic_reference_plan_第1话.json | P016 多人同框主色撞色（易串脸）：CHAR_WANG↔CHAR_CHEN（同主色「白」）——用互斥发色/服装主色/配饰强分，必要时拆反打。 | identity | 按处方补该角色缺的视图/表情/服装参考并重建出图包。 |
| warn | multi_character_closeup | 生产数据/comic_reference_plan_第1话.json | P016 多人近景=串脸最高发档：优先拆单人CU+反打或降景别，坚持同框须登记分区/分别出图+合成。 | identity | 按处方补该角色缺的视图/表情/服装参考并重建出图包。 |
