# 漫画 Gate — review — 第1话

- 生成时间：2026-07-21T22:13:41
- 结论：warn
- block/warn/info：0 / 101 / 9

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
- panel_variety: panels=16 近重复对=0（advisory·不阻断）
- style consistency refreshed: 生产数据/comic_style_consistency_第1话.md
- character consistency refreshed: 生产数据/comic_character_consistency_第1话.md
- scene/prop consistency refreshed: 生产数据/comic_scene_prop_consistency_第1话.md
- comic-review report refreshed in review gate
- drift_report: 追踪 5 角色 · 有漂移 4（跨话汇总·advisory）

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
| warn | outer_panel_frame | 出图/第1话/panels/P005.png | 检测到疑似模型画出的外框/截图边，正式面板不能自带边框。 | image | 补强无外框/无截图边/画面铺满画布约束并 force 重抽该格。 |
| warn | outer_panel_frame | 出图/第1话/panels/P006.png | 检测到疑似模型画出的外框/截图边，正式面板不能自带边框。 | image | 补强无外框/无截图边/画面铺满画布约束并 force 重抽该格。 |
| warn | outer_panel_frame | 出图/第1话/panels/P007.png | 检测到疑似模型画出的外框/截图边，正式面板不能自带边框。 | image | 补强无外框/无截图边/画面铺满画布约束并 force 重抽该格。 |
| warn | outer_panel_frame | 出图/第1话/panels/P008.png | 检测到疑似模型画出的外框/截图边，正式面板不能自带边框。 | image | 补强无外框/无截图边/画面铺满画布约束并 force 重抽该格。 |
| warn | outer_panel_frame | 出图/第1话/panels/P009.png | 检测到疑似模型画出的外框/截图边，正式面板不能自带边框。 | image | 补强无外框/无截图边/画面铺满画布约束并 force 重抽该格。 |
| warn | outer_panel_frame | 出图/第1话/panels/P010.png | 检测到疑似模型画出的外框/截图边，正式面板不能自带边框。 | image | 补强无外框/无截图边/画面铺满画布约束并 force 重抽该格。 |
| warn | outer_panel_frame | 出图/第1话/panels/P011.png | 检测到疑似模型画出的外框/截图边，正式面板不能自带边框。 | image | 补强无外框/无截图边/画面铺满画布约束并 force 重抽该格。 |
| warn | outer_panel_frame | 出图/第1话/panels/P012.png | 检测到疑似模型画出的外框/截图边，正式面板不能自带边框。 | image | 补强无外框/无截图边/画面铺满画布约束并 force 重抽该格。 |
| warn | panel_style_outlier | 出图/第1话/panels/P001.png | 风格指纹内聚度 0.6497 明显低于本话中位 0.7778，疑似画风、细节密度或照片感跳变。 | image | 与全话 contact sheet 并排人审；若确实跳变，回 comic-image 用同一风格锚和参考图重抽该格。 |
| warn | tone_value_outlier | 出图/第1话/panels/P001.png | 黑白灰量化偏离话内中位：black_ratio=0.5191（中位 0.123），线宽代理 edge_density=0.0763（中位 0.099）。疑似网点密度/黑场/线宽口径不统一。 | image | 对照 finishing_plan 的 tone/black/ink 计划人审；口径确实漂了则统一收尾契约后重抽。 |
| warn | tone_value_outlier | 出图/第1话/panels/P005.png | 黑白灰量化偏离话内中位：black_ratio=0.3501（中位 0.123），线宽代理 edge_density=0.0864（中位 0.099）。疑似网点密度/黑场/线宽口径不统一。 | image | 对照 finishing_plan 的 tone/black/ink 计划人审；口径确实漂了则统一收尾契约后重抽。 |
| warn | tone_value_outlier | 出图/第1话/panels/P012.png | 黑白灰量化偏离话内中位：black_ratio=0.5788（中位 0.123），线宽代理 edge_density=0.0694（中位 0.099）。疑似网点密度/黑场/线宽口径不统一。 | image | 对照 finishing_plan 的 tone/black/ink 计划人审；口径确实漂了则统一收尾契约后重抽。 |
| warn | tone_value_outlier | 出图/第1话/panels/P013.png | 黑白灰量化偏离话内中位：black_ratio=0.3048（中位 0.123），线宽代理 edge_density=0.1209（中位 0.099）。疑似网点密度/黑场/线宽口径不统一。 | image | 对照 finishing_plan 的 tone/black/ink 计划人审；口径确实漂了则统一收尾契约后重抽。 |
| warn | tone_value_outlier | 出图/第1话/panels/P016.png | 黑白灰量化偏离话内中位：black_ratio=0.0437（中位 0.123），线宽代理 edge_density=0.1732（中位 0.099）。疑似网点密度/黑场/线宽口径不统一。 | image | 对照 finishing_plan 的 tone/black/ink 计划人审；口径确实漂了则统一收尾契约后重抽。 |
| warn | hair_fingerprint_low | 出图/第1话/panels/P011.png | CHAR_CHEN hair 指纹与参考图相似度偏低：score=0.437。这是色彩分布代理，需并排人审。 | image | 查看 character consistency contact sheet；如确实换脸/换发型/换服装，回 comic-image 用同一参考组重抽该格。 |
| warn | hair_fingerprint_low | 出图/第1话/panels/P012.png | CHAR_CHEN hair 指纹与参考图相似度偏低：score=0.410。这是色彩分布代理，需并排人审。 | image | 查看 character consistency contact sheet；如确实换脸/换发型/换服装，回 comic-image 用同一参考组重抽该格。 |
| warn | hair_fingerprint_low | 出图/第1话/panels/P006.png | CHAR_DAOIST hair 指纹与参考图相似度偏低：score=0.319。这是色彩分布代理，需并排人审。 | image | 查看 character consistency contact sheet；如确实换脸/换发型/换服装，回 comic-image 用同一参考组重抽该格。 |
| warn | face_fingerprint_low | 出图/第1话/panels/P002.png | CHAR_WANG face 指纹与参考图相似度偏低：score=0.452。这是色彩分布代理，需并排人审。 | image | 查看 character consistency contact sheet；如确实换脸/换发型/换服装，回 comic-image 用同一参考组重抽该格。 |
| warn | hair_fingerprint_low | 出图/第1话/panels/P004.png | CHAR_WANG hair 指纹与参考图相似度偏低：score=0.430。这是色彩分布代理，需并排人审。 | image | 查看 character consistency contact sheet；如确实换脸/换发型/换服装，回 comic-image 用同一参考组重抽该格。 |
| warn | outfit_fingerprint_low | 出图/第1话/panels/P005.png | CHAR_WANG outfit 指纹与参考图相似度偏低：score=0.382。这是色彩分布代理，需并排人审。 | image | 查看 character consistency contact sheet；如确实换脸/换发型/换服装，回 comic-image 用同一参考组重抽该格。 |
| warn | face_fingerprint_low | 出图/第1话/panels/P006.png | CHAR_WANG face 指纹与参考图相似度偏低：score=0.450。这是色彩分布代理，需并排人审。 | image | 查看 character consistency contact sheet；如确实换脸/换发型/换服装，回 comic-image 用同一参考组重抽该格。 |
| warn | hair_fingerprint_low | 出图/第1话/panels/P006.png | CHAR_WANG hair 指纹与参考图相似度偏低：score=0.275。这是色彩分布代理，需并排人审。 | image | 查看 character consistency contact sheet；如确实换脸/换发型/换服装，回 comic-image 用同一参考组重抽该格。 |
| warn | face_fingerprint_low | 出图/第1话/panels/P007.png | CHAR_WANG face 指纹与参考图相似度偏低：score=0.427。这是色彩分布代理，需并排人审。 | image | 查看 character consistency contact sheet；如确实换脸/换发型/换服装，回 comic-image 用同一参考组重抽该格。 |
| warn | hair_fingerprint_low | 出图/第1话/panels/P007.png | CHAR_WANG hair 指纹与参考图相似度偏低：score=0.424。这是色彩分布代理，需并排人审。 | image | 查看 character consistency contact sheet；如确实换脸/换发型/换服装，回 comic-image 用同一参考组重抽该格。 |
| warn | hair_fingerprint_low | 出图/第1话/panels/P001.png | MON_PAINTED_SKIN hair 指纹与参考图相似度偏低：score=0.429。这是色彩分布代理，需并排人审。 | image | 查看 character consistency contact sheet；如确实换脸/换发型/换服装，回 comic-image 用同一参考组重抽该格。 |
| warn | vlm_judge_unadjudicated | 生产数据/comic_vlm_judge_tasks_第1话.json | VLM 并排判定任务包已生成 46 条但 0 条裁决——角色/生物身份、背景、道具三轴机检空转，画错生物形态这类漂移不会被拦。 | review | 用 vlm_adjudicate.py queue 出队、由多模态 agent 看图打分后 submit 回写 生产数据/comic_vlm_judge_verdicts_第1话.json；或恢复 CCIP（comicqc env）后重跑 gate。 |
| warn | platform_profile_unverified | 排版/export_manifest.json | 自定义(红果式移动端节奏内审，不作为发布平台规格) 平台规格未有当前可机检的一手尺寸证据。 | compose | 发布/商用前在平台后台或官方文档核验宽度、高度、格式、文件大小，并更新 platform profile。 |
| info | cross_chapter_drift | 生产数据/comic_identity_drift_report.json | CHAR_CHEN 首崩 第1话：CHAR_CHEN：仅 第1话 单话漂移——按该话 identity report 的 rerun_targets 重抽受影响格即可，先不升重资产。 | identity | 看 comic_identity_drift_report 决定补参考/补服装/补专门定妆或换后端。 |
| info | cross_chapter_drift | 生产数据/comic_identity_drift_report.json | CHAR_DAOIST 首崩 第1话：CHAR_DAOIST：仅 第1话 单话漂移——按该话 identity report 的 rerun_targets 重抽受影响格即可，先不升重资产。 | identity | 看 comic_identity_drift_report 决定补参考/补服装/补专门定妆或换后端。 |
| info | cross_chapter_drift | 生产数据/comic_identity_drift_report.json | CHAR_WANG 首崩 第1话：CHAR_WANG：第1话 服装漂移——在 registry.assets 的 outfits 子注册登记该换装（描述+参考图+绝不清单），重抽换装格；锁脸锁不住领型/纽扣/花纹。 | identity | 看 comic_identity_drift_report 决定补参考/补服装/补专门定妆或换后端。 |
| info | cross_chapter_drift | 生产数据/comic_identity_drift_report.json | MON_PAINTED_SKIN 首崩 第1话：MON_PAINTED_SKIN：仅 第1话 单话漂移——按该话 identity report 的 rerun_targets 重抽受影响格即可，先不升重资产。 | identity | 看 comic_identity_drift_report 决定补参考/补服装/补专门定妆或换后端。 |
| warn | visual_contract | 脚本/第1话/panel_script.json#P001 | P001 的人物完整性契约未同时覆盖脸/眼/发和手脚/身体/关键道具 | comic-script | 补脸型、眼型/眼距、发际线、发型、服装标志、手脚和关键道具完整性 |
| warn | visual_contract | 脚本/第1话/panel_script.json#P006 | P006 的人物完整性契约未同时覆盖脸/眼/发和手脚/身体/关键道具 | comic-script | 补脸型、眼型/眼距、发际线、发型、服装标志、手脚和关键道具完整性 |
| warn | visual_contract | 脚本/第1话/panel_script.json#P008 | P008 的人物完整性契约未同时覆盖脸/眼/发和手脚/身体/关键道具 | comic-script | 补脸型、眼型/眼距、发际线、发型、服装标志、手脚和关键道具完整性 |
| warn | visual_contract | 脚本/第1话/panel_script.json#P009 | P009 的人物完整性契约未同时覆盖脸/眼/发和手脚/身体/关键道具 | comic-script | 补脸型、眼型/眼距、发际线、发型、服装标志、手脚和关键道具完整性 |
| warn | visual_contract | 脚本/第1话/panel_script.json#P011 | P011 的人物完整性契约未同时覆盖脸/眼/发和手脚/身体/关键道具 | comic-script | 补脸型、眼型/眼距、发际线、发型、服装标志、手脚和关键道具完整性 |
| warn | visual_contract | 脚本/第1话/panel_script.json#P012 | P012 的人物完整性契约未同时覆盖脸/眼/发和手脚/身体/关键道具 | comic-script | 补脸型、眼型/眼距、发际线、发型、服装标志、手脚和关键道具完整性 |
| warn | visual_contract | 脚本/第1话/panel_script.json#P013 | P013 的人物完整性契约未同时覆盖脸/眼/发和手脚/身体/关键道具 | comic-script | 补脸型、眼型/眼距、发际线、发型、服装标志、手脚和关键道具完整性 |
| warn | visual_contract | 脚本/第1话/panel_script.json#P014 | P014 的人物完整性契约未同时覆盖脸/眼/发和手脚/身体/关键道具 | comic-script | 补脸型、眼型/眼距、发际线、发型、服装标志、手脚和关键道具完整性 |
| warn | visual_contract | 脚本/第1话/panel_script.json#P015 | P015 的人物完整性契约未同时覆盖脸/眼/发和手脚/身体/关键道具 | comic-script | 补脸型、眼型/眼距、发际线、发型、服装标志、手脚和关键道具完整性 |
| warn | visual_contract | 脚本/第1话/panel_script.json#P016 | P016 的人物完整性契约未同时覆盖脸/眼/发和手脚/身体/关键道具 | comic-script | 补脸型、眼型/眼距、发际线、发型、服装标志、手脚和关键道具完整性 |
| info | lettering | 排版/第1话/export_manifest.json | manifest 未记录嵌字槽位 QC 接触表，长条图过高时不便逐字复核 | comic-compose | 用 export_longstrip.py --render --qc-slots 重新导出 |
| warn | export | 排版/export_manifest.json | 自定义(红果式移动端节奏内审，不作为发布平台规格) 平台规格未有当前可机检的一手尺寸证据。 | comic-compose | 发布/商用前在平台后台或官方文档核验宽度、高度、格式、文件大小，并更新 platform profile。 |
| warn | style | 出图/第1话/panels/P005.png | 检测到疑似模型画出的外框/截图边，正式面板不能自带边框。 | comic-image | 补强无外框/无截图边/画面铺满画布约束并 force 重抽该格。 |
| warn | style | 出图/第1话/panels/P006.png | 检测到疑似模型画出的外框/截图边，正式面板不能自带边框。 | comic-image | 补强无外框/无截图边/画面铺满画布约束并 force 重抽该格。 |
| warn | style | 出图/第1话/panels/P007.png | 检测到疑似模型画出的外框/截图边，正式面板不能自带边框。 | comic-image | 补强无外框/无截图边/画面铺满画布约束并 force 重抽该格。 |
| warn | style | 出图/第1话/panels/P008.png | 检测到疑似模型画出的外框/截图边，正式面板不能自带边框。 | comic-image | 补强无外框/无截图边/画面铺满画布约束并 force 重抽该格。 |
| warn | style | 出图/第1话/panels/P009.png | 检测到疑似模型画出的外框/截图边，正式面板不能自带边框。 | comic-image | 补强无外框/无截图边/画面铺满画布约束并 force 重抽该格。 |
| warn | style | 出图/第1话/panels/P010.png | 检测到疑似模型画出的外框/截图边，正式面板不能自带边框。 | comic-image | 补强无外框/无截图边/画面铺满画布约束并 force 重抽该格。 |
| warn | style | 出图/第1话/panels/P011.png | 检测到疑似模型画出的外框/截图边，正式面板不能自带边框。 | comic-image | 补强无外框/无截图边/画面铺满画布约束并 force 重抽该格。 |
| warn | style | 出图/第1话/panels/P012.png | 检测到疑似模型画出的外框/截图边，正式面板不能自带边框。 | comic-image | 补强无外框/无截图边/画面铺满画布约束并 force 重抽该格。 |
| warn | style | 出图/第1话/panels/P001.png | 风格指纹内聚度 0.6497 明显低于本话中位 0.7778，疑似画风、细节密度或照片感跳变。 | comic-image | 与全话 contact sheet 并排人审；若确实跳变，回 comic-image 用同一风格锚和参考图重抽该格。 |
| warn | style | 出图/第1话/panels/P001.png | 黑白灰量化偏离话内中位：black_ratio=0.5191（中位 0.123），线宽代理 edge_density=0.0763（中位 0.099）。疑似网点密度/黑场/线宽口径不统一。 | comic-image | 对照 finishing_plan 的 tone/black/ink 计划人审；口径确实漂了则统一收尾契约后重抽。 |
| warn | style | 出图/第1话/panels/P005.png | 黑白灰量化偏离话内中位：black_ratio=0.3501（中位 0.123），线宽代理 edge_density=0.0864（中位 0.099）。疑似网点密度/黑场/线宽口径不统一。 | comic-image | 对照 finishing_plan 的 tone/black/ink 计划人审；口径确实漂了则统一收尾契约后重抽。 |
| warn | style | 出图/第1话/panels/P012.png | 黑白灰量化偏离话内中位：black_ratio=0.5788（中位 0.123），线宽代理 edge_density=0.0694（中位 0.099）。疑似网点密度/黑场/线宽口径不统一。 | comic-image | 对照 finishing_plan 的 tone/black/ink 计划人审；口径确实漂了则统一收尾契约后重抽。 |
| warn | style | 出图/第1话/panels/P013.png | 黑白灰量化偏离话内中位：black_ratio=0.3048（中位 0.123），线宽代理 edge_density=0.1209（中位 0.099）。疑似网点密度/黑场/线宽口径不统一。 | comic-image | 对照 finishing_plan 的 tone/black/ink 计划人审；口径确实漂了则统一收尾契约后重抽。 |
| warn | style | 出图/第1话/panels/P016.png | 黑白灰量化偏离话内中位：black_ratio=0.0437（中位 0.123），线宽代理 edge_density=0.1732（中位 0.099）。疑似网点密度/黑场/线宽口径不统一。 | comic-image | 对照 finishing_plan 的 tone/black/ink 计划人审；口径确实漂了则统一收尾契约后重抽。 |
| warn | character | 出图/第1话/panels/P011.png | CHAR_CHEN hair 指纹与参考图相似度偏低：score=0.437。这是色彩分布代理，需并排人审。 | comic-image | 查看 character consistency contact sheet；如确实换脸/换发型/换服装，回 comic-image 用同一参考组重抽该格。 |
| warn | character | 出图/第1话/panels/P012.png | CHAR_CHEN hair 指纹与参考图相似度偏低：score=0.410。这是色彩分布代理，需并排人审。 | comic-image | 查看 character consistency contact sheet；如确实换脸/换发型/换服装，回 comic-image 用同一参考组重抽该格。 |
| warn | character | 出图/第1话/panels/P006.png | CHAR_DAOIST hair 指纹与参考图相似度偏低：score=0.319。这是色彩分布代理，需并排人审。 | comic-image | 查看 character consistency contact sheet；如确实换脸/换发型/换服装，回 comic-image 用同一参考组重抽该格。 |
| warn | character | 出图/第1话/panels/P002.png | CHAR_WANG face 指纹与参考图相似度偏低：score=0.452。这是色彩分布代理，需并排人审。 | comic-image | 查看 character consistency contact sheet；如确实换脸/换发型/换服装，回 comic-image 用同一参考组重抽该格。 |
| warn | character | 出图/第1话/panels/P004.png | CHAR_WANG hair 指纹与参考图相似度偏低：score=0.430。这是色彩分布代理，需并排人审。 | comic-image | 查看 character consistency contact sheet；如确实换脸/换发型/换服装，回 comic-image 用同一参考组重抽该格。 |
| warn | character | 出图/第1话/panels/P005.png | CHAR_WANG outfit 指纹与参考图相似度偏低：score=0.382。这是色彩分布代理，需并排人审。 | comic-image | 查看 character consistency contact sheet；如确实换脸/换发型/换服装，回 comic-image 用同一参考组重抽该格。 |
| warn | character | 出图/第1话/panels/P006.png | CHAR_WANG face 指纹与参考图相似度偏低：score=0.450。这是色彩分布代理，需并排人审。 | comic-image | 查看 character consistency contact sheet；如确实换脸/换发型/换服装，回 comic-image 用同一参考组重抽该格。 |
| warn | character | 出图/第1话/panels/P006.png | CHAR_WANG hair 指纹与参考图相似度偏低：score=0.275。这是色彩分布代理，需并排人审。 | comic-image | 查看 character consistency contact sheet；如确实换脸/换发型/换服装，回 comic-image 用同一参考组重抽该格。 |
| warn | character | 出图/第1话/panels/P007.png | CHAR_WANG face 指纹与参考图相似度偏低：score=0.427。这是色彩分布代理，需并排人审。 | comic-image | 查看 character consistency contact sheet；如确实换脸/换发型/换服装，回 comic-image 用同一参考组重抽该格。 |
| warn | character | 出图/第1话/panels/P007.png | CHAR_WANG hair 指纹与参考图相似度偏低：score=0.424。这是色彩分布代理，需并排人审。 | comic-image | 查看 character consistency contact sheet；如确实换脸/换发型/换服装，回 comic-image 用同一参考组重抽该格。 |
| warn | character | 出图/第1话/panels/P001.png | MON_PAINTED_SKIN hair 指纹与参考图相似度偏低：score=0.429。这是色彩分布代理，需并排人审。 | comic-image | 查看 character consistency contact sheet；如确实换脸/换发型/换服装，回 comic-image 用同一参考组重抽该格。 |
