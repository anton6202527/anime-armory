# 漫画 Gate — image — 第5话

- 生成时间：2026-07-19T16:52:31
- 结论：warn
- block/warn/info：0 / 84 / 4

## 记录

- 开发包严格合同: pass
- 源范围/SHA/逐格 coverage 合同: pass
- continuity_audit: chapters=5 block=0 warn=0
- 缩略分镜/name board 审批合同: pass
- 排版审批合同: pass
- 原稿收尾合同: pass
- backend adapter: dreamina_image2image; reference_image_limit=10; persistent_subject=False
- 角色注册表 v2: pass
- 角色多视图技术齐套与人审签收: pass
- chapter_beat_audit: must=0 warn=1（advisory·不阻断）
- setup_payoff_ledger: must=0 warn=0（advisory·不阻断）
- reentry_context_audit: must=0 warn=0（advisory·不阻断）
- entity_presence_audit: must=0 warn=3（advisory·不阻断）
- redundancy_audit: must=0 warn=0（advisory·不阻断）
- subtext_audit: must=0 warn=0（advisory·不阻断）
- reference_planner: 含角色格 41 需处理 28；处方 SHA 已校验
- panel_variety: panels=48 近重复对=0（advisory·不阻断）
- style consistency refreshed: 生产数据/comic_style_consistency_第5话.md
- character consistency refreshed: 生产数据/comic_character_consistency_第5话.md
- scene/prop consistency refreshed: 生产数据/comic_scene_prop_consistency_第5话.md

## Findings

| severity | code | artifact | reason | return_to | suggested_fix |
|---|---|---|---|---|---|
| warn | ending_mode_mismatch | 生产数据/comic_chapter_beat_audit_第5话.json | 合同 ending_mode=closure_with_new_promise，末格 story_function=ending_promise；期望候选为 ['hook', 'new_promise', 'resolution']。这是编辑复核提示，不是硬闸。 | comic-script | 按机检建议回 comic-script 修分话/分格后重跑。 |
| info | climax_at_tail | 生产数据/comic_chapter_beat_audit_第5话.json | 高潮候选在 94%；确认中段是否有足够支撑。 | comic-script | 按机检建议回 comic-script 修分话/分格后重跑。 |
| warn | mentioned_not_bound | 生产数据/comic_entity_presence_audit_第5话.json | P003 画面描述提到「王进」（registry 实体 CHAR_WANG_JIN），但该格 characters/references/scene_anchor 都没绑它——出图不会附其定妆参考，形态全靠模型自由发挥。确认入画则补进该格 references（或 characters），不入画则改写描述。 | comic-script | 按机检建议回 comic-script 修分话/分格后重跑。 |
| warn | mentioned_not_bound | 生产数据/comic_entity_presence_audit_第5话.json | P018 画面描述提到「王进」（registry 实体 CHAR_WANG_JIN），但该格 characters/references/scene_anchor 都没绑它——出图不会附其定妆参考，形态全靠模型自由发挥。确认入画则补进该格 references（或 characters），不入画则改写描述。 | comic-script | 按机检建议回 comic-script 修分话/分格后重跑。 |
| warn | mentioned_not_bound | 生产数据/comic_entity_presence_audit_第5话.json | P047 画面描述提到「高俅」（registry 实体 CHAR_GAO_QIU），但该格 characters/references/scene_anchor 都没绑它——出图不会附其定妆参考，形态全靠模型自由发挥。确认入画则补进该格 references（或 characters），不入画则改写描述。 | comic-script | 按机检建议回 comic-script 修分话/分格后重跑。 |
| warn | same_frame_color_collision | 生产数据/comic_reference_plan_第5话.json | P005 多人同框主色撞色（易串脸）：CHAR_WANG_JIN↔CHAR_WANG_MOTHER（同主色「白」）——用互斥发色/服装主色/配饰强分，必要时拆反打。 | identity | 按处方补该角色缺的视图/表情/服装参考并重建出图包。 |
| warn | same_frame_color_collision | 生产数据/comic_reference_plan_第5话.json | P011 多人同框主色撞色（易串脸）：CHAR_WANG_JIN↔CHAR_WANG_MOTHER（同主色「白」）——用互斥发色/服装主色/配饰强分，必要时拆反打。 | identity | 按处方补该角色缺的视图/表情/服装参考并重建出图包。 |
| warn | same_frame_color_collision | 生产数据/comic_reference_plan_第5话.json | P012 多人同框主色撞色（易串脸）：CHAR_WANG_JIN↔CHAR_WANG_MOTHER（同主色「白」）——用互斥发色/服装主色/配饰强分，必要时拆反打。 | identity | 按处方补该角色缺的视图/表情/服装参考并重建出图包。 |
| warn | same_frame_color_collision | 生产数据/comic_reference_plan_第5话.json | P013 多人同框主色撞色（易串脸）：CHAR_WANG_JIN↔CHAR_WANG_MOTHER（同主色「白」）——用互斥发色/服装主色/配饰强分，必要时拆反打。 | identity | 按处方补该角色缺的视图/表情/服装参考并重建出图包。 |
| warn | same_frame_color_collision | 生产数据/comic_reference_plan_第5话.json | P014 多人同框主色撞色（易串脸）：CHAR_WANG_JIN↔CHAR_WANG_MOTHER（同主色「白」）——用互斥发色/服装主色/配饰强分，必要时拆反打。 | identity | 按处方补该角色缺的视图/表情/服装参考并重建出图包。 |
| warn | same_frame_color_collision | 生产数据/comic_reference_plan_第5话.json | P019 多人同框主色撞色（易串脸）：CHAR_WANG_JIN↔CHAR_WANG_MOTHER（同主色「白」）——用互斥发色/服装主色/配饰强分，必要时拆反打。 | identity | 按处方补该角色缺的视图/表情/服装参考并重建出图包。 |
| warn | same_frame_color_collision | 生产数据/comic_reference_plan_第5话.json | P020 多人同框主色撞色（易串脸）：CHAR_WANG_JIN↔CHAR_WANG_MOTHER（同主色「白」）——用互斥发色/服装主色/配饰强分，必要时拆反打。 | identity | 按处方补该角色缺的视图/表情/服装参考并重建出图包。 |
| warn | same_frame_color_collision | 生产数据/comic_reference_plan_第5话.json | P021 多人同框主色撞色（易串脸）：CHAR_WANG_JIN↔CHAR_WANG_MOTHER（同主色「白」）——用互斥发色/服装主色/配饰强分，必要时拆反打。 | identity | 按处方补该角色缺的视图/表情/服装参考并重建出图包。 |
| warn | same_frame_color_collision | 生产数据/comic_reference_plan_第5话.json | P022 多人同框主色撞色（易串脸）：CHAR_WANG_JIN↔CHAR_WANG_MOTHER（同主色「白」）——用互斥发色/服装主色/配饰强分，必要时拆反打。 | identity | 按处方补该角色缺的视图/表情/服装参考并重建出图包。 |
| warn | same_frame_color_collision | 生产数据/comic_reference_plan_第5话.json | P027 多人同框主色撞色（易串脸）：CHAR_WANG_JIN↔CHAR_WANG_MOTHER（同主色「白」）——用互斥发色/服装主色/配饰强分，必要时拆反打。 | identity | 按处方补该角色缺的视图/表情/服装参考并重建出图包。 |
| warn | same_frame_color_collision | 生产数据/comic_reference_plan_第5话.json | P028 多人同框主色撞色（易串脸）：CHAR_WANG_JIN↔CHAR_WANG_MOTHER（同主色「白」）——用互斥发色/服装主色/配饰强分，必要时拆反打。 | identity | 按处方补该角色缺的视图/表情/服装参考并重建出图包。 |
| warn | missing_reference | 生产数据/comic_reference_plan_第5话.json | P029·史太公：缺 45°/three_quarter 参考（档位或本格变化量需要） | identity | 按处方补该角色缺的视图/表情/服装参考并重建出图包。 |
| warn | missing_reference | 生产数据/comic_reference_plan_第5话.json | P029·史太公：缺 45°/¾ 侧脸参考（动作格主身份锚·避免 frontal 摆拍偏置） | identity | 按处方补该角色缺的视图/表情/服装参考并重建出图包。 |
| warn | same_frame_color_collision | 生产数据/comic_reference_plan_第5话.json | P029 多人同框主色撞色（易串脸）：CHAR_SHI_TAIGONG↔CHAR_WANG_JIN（同主色「白」）、CHAR_SHI_TAIGONG↔CHAR_WANG_MOTHER（同主色「白」）、CHAR_WANG_JIN↔CHAR_WANG_MOTHER（同主色「白」）——用互斥发色/服装主色/配饰强分，必要时拆反打。 | identity | 按处方补该角色缺的视图/表情/服装参考并重建出图包。 |
| warn | missing_reference | 生产数据/comic_reference_plan_第5话.json | P030·史太公：缺 45°/three_quarter 参考（档位或本格变化量需要） | identity | 按处方补该角色缺的视图/表情/服装参考并重建出图包。 |
| warn | missing_reference | 生产数据/comic_reference_plan_第5话.json | P030·史太公：缺 45°/¾ 侧脸参考（动作格主身份锚·避免 frontal 摆拍偏置） | identity | 按处方补该角色缺的视图/表情/服装参考并重建出图包。 |
| warn | same_frame_color_collision | 生产数据/comic_reference_plan_第5话.json | P030 多人同框主色撞色（易串脸）：CHAR_SHI_TAIGONG↔CHAR_WANG_JIN（同主色「白」）、CHAR_SHI_TAIGONG↔CHAR_WANG_MOTHER（同主色「白」）、CHAR_WANG_JIN↔CHAR_WANG_MOTHER（同主色「白」）——用互斥发色/服装主色/配饰强分，必要时拆反打。 | identity | 按处方补该角色缺的视图/表情/服装参考并重建出图包。 |
| warn | same_frame_color_collision | 生产数据/comic_reference_plan_第5话.json | P031 多人同框主色撞色（易串脸）：CHAR_WANG_JIN↔CHAR_WANG_MOTHER（同主色「白」）——用互斥发色/服装主色/配饰强分，必要时拆反打。 | identity | 按处方补该角色缺的视图/表情/服装参考并重建出图包。 |
| warn | missing_reference | 生产数据/comic_reference_plan_第5话.json | P032·史太公：缺 45°/three_quarter 参考（档位或本格变化量需要） | identity | 按处方补该角色缺的视图/表情/服装参考并重建出图包。 |
| warn | missing_reference | 生产数据/comic_reference_plan_第5话.json | P032·史太公：缺 45°/¾ 侧脸参考（动作格主身份锚·避免 frontal 摆拍偏置） | identity | 按处方补该角色缺的视图/表情/服装参考并重建出图包。 |
| warn | same_frame_color_collision | 生产数据/comic_reference_plan_第5话.json | P032 多人同框主色撞色（易串脸）：CHAR_SHI_TAIGONG↔CHAR_WANG_JIN（同主色「白」）、CHAR_SHI_TAIGONG↔CHAR_WANG_MOTHER（同主色「白」）、CHAR_WANG_JIN↔CHAR_WANG_MOTHER（同主色「白」）——用互斥发色/服装主色/配饰强分，必要时拆反打。 | identity | 按处方补该角色缺的视图/表情/服装参考并重建出图包。 |
| warn | same_frame_color_collision | 生产数据/comic_reference_plan_第5话.json | P033 多人同框主色撞色（易串脸）：CHAR_WANG_MOTHER↔CHAR_WANG_JIN（同主色「白」）——用互斥发色/服装主色/配饰强分，必要时拆反打。 | identity | 按处方补该角色缺的视图/表情/服装参考并重建出图包。 |
| warn | missing_reference | 生产数据/comic_reference_plan_第5话.json | P038·史太公：缺 45°/three_quarter 参考（档位或本格变化量需要） | identity | 按处方补该角色缺的视图/表情/服装参考并重建出图包。 |
| warn | missing_reference | 生产数据/comic_reference_plan_第5话.json | P038·史太公：缺 45°/¾ 侧脸参考（动作格主身份锚·避免 frontal 摆拍偏置） | identity | 按处方补该角色缺的视图/表情/服装参考并重建出图包。 |
| warn | same_frame_color_collision | 生产数据/comic_reference_plan_第5话.json | P038 多人同框主色撞色（易串脸）：CHAR_SHI_TAIGONG↔CHAR_WANG_JIN（同主色「白」）——用互斥发色/服装主色/配饰强分，必要时拆反打。 | identity | 按处方补该角色缺的视图/表情/服装参考并重建出图包。 |
| warn | missing_reference | 生产数据/comic_reference_plan_第5话.json | P047·史太公：缺 45°/three_quarter 参考（档位或本格变化量需要） | identity | 按处方补该角色缺的视图/表情/服装参考并重建出图包。 |
| warn | missing_reference | 生产数据/comic_reference_plan_第5话.json | P047·史太公：缺 45°/¾ 侧脸参考（动作格主身份锚·避免 frontal 摆拍偏置） | identity | 按处方补该角色缺的视图/表情/服装参考并重建出图包。 |
| warn | same_frame_color_collision | 生产数据/comic_reference_plan_第5话.json | P047 多人同框主色撞色（易串脸）：CHAR_WANG_JIN↔CHAR_SHI_TAIGONG（同主色「白」）、CHAR_WANG_JIN↔CHAR_WANG_MOTHER（同主色「白」）、CHAR_SHI_TAIGONG↔CHAR_WANG_MOTHER（同主色「白」）——用互斥发色/服装主色/配饰强分，必要时拆反打。 | identity | 按处方补该角色缺的视图/表情/服装参考并重建出图包。 |
| info | panel_post_qc_warn | 出图/第5话/panels/P019.png | P019 的落盘 post_qc=warn 已人审签收为误报：原图目检确认候选白区为山间云雾与天空留白，不是烘焙气泡、文字框或乱码。 | review | 若该格重抽或构图变化，需要重新复核 panel_qc。 |
| info | panel_post_qc_warn | 出图/第5话/panels/P032.png | P032 的落盘 post_qc=warn 已人审签收为误报：原图目检确认候选白区为史太公白衣及院墙亮部，不是烘焙气泡、文字框或乱码。 | review | 若该格重抽或构图变化，需要重新复核 panel_qc。 |
| info | panel_post_qc_warn | 出图/第5话/panels/P037.png | P037 的落盘 post_qc=warn 已人审签收为误报：原图目检确认候选白区为较场天空与石地高光，不是烘焙气泡、文字框或乱码。 | review | 若该格重抽或构图变化，需要重新复核 panel_qc。 |
| warn | panel_style_outlier | 出图/第5话/panels/P004.png | 风格指纹内聚度 0.6576 明显低于本话中位 0.7690，疑似画风、细节密度或照片感跳变。 | image | 与全话 contact sheet 并排人审；若确实跳变，回 comic-image 用同一风格锚和参考图重抽该格。 |
| warn | panel_style_outlier | 出图/第5话/panels/P007.png | 风格指纹内聚度 0.6881 明显低于本话中位 0.7690，疑似画风、细节密度或照片感跳变。 | image | 与全话 contact sheet 并排人审；若确实跳变，回 comic-image 用同一风格锚和参考图重抽该格。 |
| warn | panel_style_outlier | 出图/第5话/panels/P012.png | 风格指纹内聚度 0.6000 明显低于本话中位 0.7690，疑似画风、细节密度或照片感跳变。 | image | 与全话 contact sheet 并排人审；若确实跳变，回 comic-image 用同一风格锚和参考图重抽该格。 |
| warn | panel_style_outlier | 出图/第5话/panels/P014.png | 风格指纹内聚度 0.7082 明显低于本话中位 0.7690，疑似画风、细节密度或照片感跳变。 | image | 与全话 contact sheet 并排人审；若确实跳变，回 comic-image 用同一风格锚和参考图重抽该格。 |
| warn | panel_style_outlier | 出图/第5话/panels/P022.png | 风格指纹内聚度 0.5620 明显低于本话中位 0.7690，疑似画风、细节密度或照片感跳变。 | image | 与全话 contact sheet 并排人审；若确实跳变，回 comic-image 用同一风格锚和参考图重抽该格。 |
| warn | panel_style_outlier | 出图/第5话/panels/P026.png | 风格指纹内聚度 0.6948 明显低于本话中位 0.7690，疑似画风、细节密度或照片感跳变。 | image | 与全话 contact sheet 并排人审；若确实跳变，回 comic-image 用同一风格锚和参考图重抽该格。 |
| warn | panel_style_outlier | 出图/第5话/panels/P027.png | 风格指纹内聚度 0.6739 明显低于本话中位 0.7690，疑似画风、细节密度或照片感跳变。 | image | 与全话 contact sheet 并排人审；若确实跳变，回 comic-image 用同一风格锚和参考图重抽该格。 |
| warn | panel_style_outlier | 出图/第5话/panels/P031.png | 风格指纹内聚度 0.7124 明显低于本话中位 0.7690，疑似画风、细节密度或照片感跳变。 | image | 与全话 contact sheet 并排人审；若确实跳变，回 comic-image 用同一风格锚和参考图重抽该格。 |
| warn | panel_style_outlier | 出图/第5话/panels/P034.png | 风格指纹内聚度 0.5653 明显低于本话中位 0.7690，疑似画风、细节密度或照片感跳变。 | image | 与全话 contact sheet 并排人审；若确实跳变，回 comic-image 用同一风格锚和参考图重抽该格。 |
| warn | location_color_grade_shift | 出图/第5话/panels/P034.png | 同场景“LOC_SHI_TRAINING_YARD”内调色代理偏离组中位：warmth_dev=0.542, tint_dev=0.043。 | image | 人审确认是否为有意光效；否则统一白平衡/冷暖光口径后重抽该格。 |
| warn | location_color_grade_shift | 出图/第5话/panels/P012.png | 同场景“LOC_WANG_JIN_HOME”内调色代理偏离组中位：warmth_dev=0.429, tint_dev=0.044。 | image | 人审确认是否为有意光效；否则统一白平衡/冷暖光口径后重抽该格。 |
| warn | adjacent_panel_grade_jump | 出图/第5话/panels/P004.png | 与同场景锚 LOC_WANG_JIN_HOME 的前一格 P003 相比冷暖/亮度跳变：warmth_jump=0.158, val_jump=0.353；疑似光位翻转或昼夜漂移。 | image | 并排两格人审；非剧情光效则按场景锚 lighting_anchor 重抽该格。 |
| warn | adjacent_panel_grade_jump | 出图/第5话/panels/P005.png | 与同场景锚 LOC_WANG_JIN_HOME 的前一格 P004 相比冷暖/亮度跳变：warmth_jump=0.129, val_jump=0.352；疑似光位翻转或昼夜漂移。 | image | 并排两格人审；非剧情光效则按场景锚 lighting_anchor 重抽该格。 |
| warn | adjacent_panel_grade_jump | 出图/第5话/panels/P023.png | 与同场景锚 LOC_SHI_MANOR 的前一格 P022 相比冷暖/亮度跳变：warmth_jump=0.075, val_jump=0.419；疑似光位翻转或昼夜漂移。 | image | 并排两格人审；非剧情光效则按场景锚 lighting_anchor 重抽该格。 |
| warn | adjacent_panel_grade_jump | 出图/第5话/panels/P035.png | 与同场景锚 LOC_SHI_TRAINING_YARD 的前一格 P034 相比冷暖/亮度跳变：warmth_jump=0.626, val_jump=0.312；疑似光位翻转或昼夜漂移。 | image | 并排两格人审；非剧情光效则按场景锚 lighting_anchor 重抽该格。 |
| warn | tone_value_outlier | 出图/第5话/panels/P002.png | 黑白灰量化偏离话内中位：black_ratio=0.3556（中位 0.029），线宽代理 edge_density=0.1029（中位 0.116）。疑似网点密度/黑场/线宽口径不统一。 | image | 对照 finishing_plan 的 tone/black/ink 计划人审；口径确实漂了则统一收尾契约后重抽。 |
| warn | tone_value_outlier | 出图/第5话/panels/P004.png | 黑白灰量化偏离话内中位：black_ratio=0.3496（中位 0.029），线宽代理 edge_density=0.0674（中位 0.116）。疑似网点密度/黑场/线宽口径不统一。 | image | 对照 finishing_plan 的 tone/black/ink 计划人审；口径确实漂了则统一收尾契约后重抽。 |
| warn | tone_value_outlier | 出图/第5话/panels/P012.png | 黑白灰量化偏离话内中位：black_ratio=0.3136（中位 0.029），线宽代理 edge_density=0.0547（中位 0.116）。疑似网点密度/黑场/线宽口径不统一。 | image | 对照 finishing_plan 的 tone/black/ink 计划人审；口径确实漂了则统一收尾契约后重抽。 |
| warn | tone_value_outlier | 出图/第5话/panels/P022.png | 黑白灰量化偏离话内中位：black_ratio=0.3304（中位 0.029），线宽代理 edge_density=0.0753（中位 0.116）。疑似网点密度/黑场/线宽口径不统一。 | image | 对照 finishing_plan 的 tone/black/ink 计划人审；口径确实漂了则统一收尾契约后重抽。 |
| warn | tone_value_outlier | 出图/第5话/panels/P034.png | 黑白灰量化偏离话内中位：black_ratio=0.2195（中位 0.029），线宽代理 edge_density=0.0647（中位 0.116）。疑似网点密度/黑场/线宽口径不统一。 | image | 对照 finishing_plan 的 tone/black/ink 计划人审；口径确实漂了则统一收尾契约后重抽。 |
| warn | tone_value_outlier | 出图/第5话/panels/P036.png | 黑白灰量化偏离话内中位：black_ratio=0.3457（中位 0.029），线宽代理 edge_density=0.1169（中位 0.116）。疑似网点密度/黑场/线宽口径不统一。 | image | 对照 finishing_plan 的 tone/black/ink 计划人审；口径确实漂了则统一收尾契约后重抽。 |
| warn | tone_value_outlier | 出图/第5话/panels/P044.png | 黑白灰量化偏离话内中位：black_ratio=0.2594（中位 0.029），线宽代理 edge_density=0.116（中位 0.116）。疑似网点密度/黑场/线宽口径不统一。 | image | 对照 finishing_plan 的 tone/black/ink 计划人审；口径确实漂了则统一收尾契约后重抽。 |
| warn | tone_value_outlier | 出图/第5话/panels/P046.png | 黑白灰量化偏离话内中位：black_ratio=0.3711（中位 0.029），线宽代理 edge_density=0.1142（中位 0.116）。疑似网点密度/黑场/线宽口径不统一。 | image | 对照 finishing_plan 的 tone/black/ink 计划人审；口径确实漂了则统一收尾契约后重抽。 |
| warn | style_anchor_drift | 出图/共享/style_baseline.json | 本话整体指纹与风格锚图最高相似度仅 0.8779，风格锚可能已失去约束力。 | image | 并排比对锚图与本话 contact sheet；必要时更新风格锚或统一重抽。 |
| warn | hair_fingerprint_low | 出图/第5话/panels/P036.png | CHAR_SHI_JIN hair 指纹与参考图相似度偏低：score=0.453。这是色彩分布代理，需并排人审。 | image | 查看 character consistency contact sheet；如确实换脸/换发型/换服装，回 comic-image 用同一参考组重抽该格。 |
| warn | hair_fingerprint_low | 出图/第5话/panels/P042.png | CHAR_SHI_JIN hair 指纹与参考图相似度偏低：score=0.446。这是色彩分布代理，需并排人审。 | image | 查看 character consistency contact sheet；如确实换脸/换发型/换服装，回 comic-image 用同一参考组重抽该格。 |
| warn | face_fingerprint_low | 出图/第5话/panels/P043.png | CHAR_SHI_JIN face 指纹与参考图相似度偏低：score=0.480。这是色彩分布代理，需并排人审。 | image | 查看 character consistency contact sheet；如确实换脸/换发型/换服装，回 comic-image 用同一参考组重抽该格。 |
| warn | hair_fingerprint_low | 出图/第5话/panels/P043.png | CHAR_SHI_JIN hair 指纹与参考图相似度偏低：score=0.369。这是色彩分布代理，需并排人审。 | image | 查看 character consistency contact sheet；如确实换脸/换发型/换服装，回 comic-image 用同一参考组重抽该格。 |
| warn | hair_fingerprint_low | 出图/第5话/panels/P046.png | CHAR_SHI_JIN hair 指纹与参考图相似度偏低：score=0.398。这是色彩分布代理，需并排人审。 | image | 查看 character consistency contact sheet；如确实换脸/换发型/换服装，回 comic-image 用同一参考组重抽该格。 |
| warn | face_fingerprint_low | 出图/第5话/panels/P004.png | CHAR_WANG_JIN face 指纹与参考图相似度偏低：score=0.435。这是色彩分布代理，需并排人审。 | image | 查看 character consistency contact sheet；如确实换脸/换发型/换服装，回 comic-image 用同一参考组重抽该格。 |
| warn | hair_fingerprint_low | 出图/第5话/panels/P004.png | CHAR_WANG_JIN hair 指纹与参考图相似度偏低：score=0.334。这是色彩分布代理，需并排人审。 | image | 查看 character consistency contact sheet；如确实换脸/换发型/换服装，回 comic-image 用同一参考组重抽该格。 |
| warn | outfit_fingerprint_low | 出图/第5话/panels/P009.png | CHAR_WANG_JIN outfit 指纹与参考图相似度偏低：score=0.384。这是色彩分布代理，需并排人审。 | image | 查看 character consistency contact sheet；如确实换脸/换发型/换服装，回 comic-image 用同一参考组重抽该格。 |
| warn | face_fingerprint_low | 出图/第5话/panels/P012.png | CHAR_WANG_JIN face 指纹与参考图相似度偏低：score=0.405。这是色彩分布代理，需并排人审。 | image | 查看 character consistency contact sheet；如确实换脸/换发型/换服装，回 comic-image 用同一参考组重抽该格。 |
| warn | hair_fingerprint_low | 出图/第5话/panels/P012.png | CHAR_WANG_JIN hair 指纹与参考图相似度偏低：score=0.385。这是色彩分布代理，需并排人审。 | image | 查看 character consistency contact sheet；如确实换脸/换发型/换服装，回 comic-image 用同一参考组重抽该格。 |
| warn | outfit_fingerprint_low | 出图/第5话/panels/P012.png | CHAR_WANG_JIN outfit 指纹与参考图相似度偏低：score=0.200。这是色彩分布代理，需并排人审。 | image | 查看 character consistency contact sheet；如确实换脸/换发型/换服装，回 comic-image 用同一参考组重抽该格。 |
| warn | face_fingerprint_low | 出图/第5话/panels/P022.png | CHAR_WANG_JIN face 指纹与参考图相似度偏低：score=0.416。这是色彩分布代理，需并排人审。 | image | 查看 character consistency contact sheet；如确实换脸/换发型/换服装，回 comic-image 用同一参考组重抽该格。 |
| warn | hair_fingerprint_low | 出图/第5话/panels/P022.png | CHAR_WANG_JIN hair 指纹与参考图相似度偏低：score=0.256。这是色彩分布代理，需并排人审。 | image | 查看 character consistency contact sheet；如确实换脸/换发型/换服装，回 comic-image 用同一参考组重抽该格。 |
| warn | face_fingerprint_low | 出图/第5话/panels/P034.png | CHAR_WANG_JIN face 指纹与参考图相似度偏低：score=0.271。这是色彩分布代理，需并排人审。 | image | 查看 character consistency contact sheet；如确实换脸/换发型/换服装，回 comic-image 用同一参考组重抽该格。 |
| warn | hair_fingerprint_low | 出图/第5话/panels/P034.png | CHAR_WANG_JIN hair 指纹与参考图相似度偏低：score=0.233。这是色彩分布代理，需并排人审。 | image | 查看 character consistency contact sheet；如确实换脸/换发型/换服装，回 comic-image 用同一参考组重抽该格。 |
| warn | outfit_fingerprint_low | 出图/第5话/panels/P034.png | CHAR_WANG_JIN outfit 指纹与参考图相似度偏低：score=0.124。这是色彩分布代理，需并排人审。 | image | 查看 character consistency contact sheet；如确实换脸/换发型/换服装，回 comic-image 用同一参考组重抽该格。 |
| warn | hair_fingerprint_low | 出图/第5话/panels/P036.png | CHAR_WANG_JIN hair 指纹与参考图相似度偏低：score=0.388。这是色彩分布代理，需并排人审。 | image | 查看 character consistency contact sheet；如确实换脸/换发型/换服装，回 comic-image 用同一参考组重抽该格。 |
| warn | outfit_fingerprint_low | 出图/第5话/panels/P036.png | CHAR_WANG_JIN outfit 指纹与参考图相似度偏低：score=0.395。这是色彩分布代理，需并排人审。 | image | 查看 character consistency contact sheet；如确实换脸/换发型/换服装，回 comic-image 用同一参考组重抽该格。 |
| warn | hair_fingerprint_low | 出图/第5话/panels/P043.png | CHAR_WANG_JIN hair 指纹与参考图相似度偏低：score=0.338。这是色彩分布代理，需并排人审。 | image | 查看 character consistency contact sheet；如确实换脸/换发型/换服装，回 comic-image 用同一参考组重抽该格。 |
| warn | face_fingerprint_low | 出图/第5话/panels/P046.png | CHAR_WANG_JIN face 指纹与参考图相似度偏低：score=0.428。这是色彩分布代理，需并排人审。 | image | 查看 character consistency contact sheet；如确实换脸/换发型/换服装，回 comic-image 用同一参考组重抽该格。 |
| warn | hair_fingerprint_low | 出图/第5话/panels/P046.png | CHAR_WANG_JIN hair 指纹与参考图相似度偏低：score=0.299。这是色彩分布代理，需并排人审。 | image | 查看 character consistency contact sheet；如确实换脸/换发型/换服装，回 comic-image 用同一参考组重抽该格。 |
| warn | face_fingerprint_low | 出图/第5话/panels/P012.png | CHAR_WANG_MOTHER face 指纹与参考图相似度偏低：score=0.287。这是色彩分布代理，需并排人审。 | image | 查看 character consistency contact sheet；如确实换脸/换发型/换服装，回 comic-image 用同一参考组重抽该格。 |
| warn | hair_fingerprint_low | 出图/第5话/panels/P012.png | CHAR_WANG_MOTHER hair 指纹与参考图相似度偏低：score=0.242。这是色彩分布代理，需并排人审。 | image | 查看 character consistency contact sheet；如确实换脸/换发型/换服装，回 comic-image 用同一参考组重抽该格。 |
| warn | outfit_fingerprint_low | 出图/第5话/panels/P012.png | CHAR_WANG_MOTHER outfit 指纹与参考图相似度偏低：score=0.363。这是色彩分布代理，需并排人审。 | image | 查看 character consistency contact sheet；如确实换脸/换发型/换服装，回 comic-image 用同一参考组重抽该格。 |
| warn | face_fingerprint_low | 出图/第5话/panels/P022.png | CHAR_WANG_MOTHER face 指纹与参考图相似度偏低：score=0.391。这是色彩分布代理，需并排人审。 | image | 查看 character consistency contact sheet；如确实换脸/换发型/换服装，回 comic-image 用同一参考组重抽该格。 |
| warn | hair_fingerprint_low | 出图/第5话/panels/P022.png | CHAR_WANG_MOTHER hair 指纹与参考图相似度偏低：score=0.194。这是色彩分布代理，需并排人审。 | image | 查看 character consistency contact sheet；如确实换脸/换发型/换服装，回 comic-image 用同一参考组重抽该格。 |
| warn | identity_similarity_engine_degraded | 生产数据/comic_character_consistency_第5话.json | CCIP 动漫身份 embedding 不可用，角色/生物相似度机检降级为色彩分布代理（同色调换脸/变形会漏报）。 | review | 独立 venv 安装 dghs-imgutils 后重跑 gate；在装好前必须以 VLM 并排裁决兜底身份轴。 |
| warn | vlm_judge_unadjudicated | 生产数据/comic_vlm_judge_tasks_第5话.json | VLM 并排判定任务包已生成 117 条但 0 条裁决——角色/生物身份、背景、道具三轴机检空转，画错生物形态这类漂移不会被拦。 | review | 由多模态 agent 逐条看图打分并写回 生产数据/comic_vlm_judge_verdicts_第5话.json 后重跑 gate。 |
