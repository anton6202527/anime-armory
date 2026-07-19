# 漫画 Gate — compose — 第6话

- 生成时间：2026-07-19T18:51:48
- 结论：warn
- block/warn/info：0 / 83 / 3

## 记录

- 开发包严格合同: pass
- 源范围/SHA/逐格 coverage 合同: pass
- continuity_audit: chapters=6 block=0 warn=0
- 缩略分镜/name board 审批合同: pass
- 排版审批合同: pass
- 原稿收尾合同: pass
- backend adapter: dreamina_image2image; reference_image_limit=10; persistent_subject=False
- 角色注册表 v2: pass
- 角色多视图技术齐套与人审签收: pass
- chapter_beat_audit: must=0 warn=2（advisory·不阻断）
- setup_payoff_ledger: must=0 warn=0（advisory·不阻断）
- reentry_context_audit: must=0 warn=0（advisory·不阻断）
- entity_presence_audit: must=0 warn=1（advisory·不阻断）
- redundancy_audit: must=0 warn=0（advisory·不阻断）
- subtext_audit: must=0 warn=0（advisory·不阻断）
- reference_planner: 含角色格 48 需处理 31；处方 SHA 已校验
- panel_variety: panels=48 近重复对=0（advisory·不阻断）
- style consistency refreshed: 生产数据/comic_style_consistency_第6话.md
- character consistency refreshed: 生产数据/comic_character_consistency_第6话.md
- scene/prop consistency refreshed: 生产数据/comic_scene_prop_consistency_第6话.md

## Findings

| severity | code | artifact | reason | return_to | suggested_fix |
|---|---|---|---|---|---|
| warn | ending_mode_mismatch | 生产数据/comic_chapter_beat_audit_第6话.json | 合同 ending_mode=closure_with_new_promise，末格 story_function=ending_promise；期望候选为 ['hook', 'new_promise', 'resolution']。这是编辑复核提示，不是硬闸。 | comic-script | 按机检建议回 comic-script 修分话/分格后重跑。 |
| warn | climax_too_early | 生产数据/comic_chapter_beat_audit_第6话.json | 最后一个高潮候选在 45%；按格序估算可能偏早，需在缩略分镜/name board 阶段结合页面/滚动几何复核。 | comic-script | 按机检建议回 comic-script 修分话/分格后重跑。 |
| warn | mentioned_not_bound | 生产数据/comic_entity_presence_audit_第6话.json | P026 画面描述提到「高俅」（registry 实体 CHAR_GAO_QIU），但该格 characters/references/scene_anchor 都没绑它——出图不会附其定妆参考，形态全靠模型自由发挥。确认入画则补进该格 references（或 characters），不入画则改写描述。 | comic-script | 按机检建议回 comic-script 修分话/分格后重跑。 |
| info | mentioned_not_bound | 生产数据/comic_entity_presence_audit_第6话.json | P045 台词/旁白提到「史太公」（registry 实体 CHAR_SHI_TAIGONG）但未绑定；若仅口头提及可忽略，若要入画需补 references。 | comic-script | 按机检建议回 comic-script 修分话/分格后重跑。 |
| warn | same_frame_color_collision | 生产数据/comic_reference_plan_第6话.json | P003 多人同框主色撞色（易串脸）：CHAR_SHI_TAIGONG↔CHAR_WANG_JIN（同主色「白」）——用互斥发色/服装主色/配饰强分，必要时拆反打。 | identity | 按处方补该角色缺的视图/表情/服装参考并重建出图包。 |
| warn | same_frame_color_collision | 生产数据/comic_reference_plan_第6话.json | P005 多人同框主色撞色（易串脸）：CHAR_SHI_TAIGONG↔CHAR_WANG_JIN（同主色「白」）——用互斥发色/服装主色/配饰强分，必要时拆反打。 | identity | 按处方补该角色缺的视图/表情/服装参考并重建出图包。 |
| warn | same_frame_color_collision | 生产数据/comic_reference_plan_第6话.json | P029 多人同框主色撞色（易串脸）：CHAR_WANG_JIN↔CHAR_WANG_MOTHER（同主色「白」）、CHAR_WANG_JIN↔CHAR_SHI_TAIGONG（同主色「白」）、CHAR_WANG_MOTHER↔CHAR_SHI_TAIGONG（同主色「白」）——用互斥发色/服装主色/配饰强分，必要时拆反打。 | identity | 按处方补该角色缺的视图/表情/服装参考并重建出图包。 |
| warn | same_frame_color_collision | 生产数据/comic_reference_plan_第6话.json | P030 多人同框主色撞色（易串脸）：CHAR_SHI_TAIGONG↔CHAR_WANG_JIN（同主色「白」）——用互斥发色/服装主色/配饰强分，必要时拆反打。 | identity | 按处方补该角色缺的视图/表情/服装参考并重建出图包。 |
| warn | same_frame_color_collision | 生产数据/comic_reference_plan_第6话.json | P033 多人同框主色撞色（易串脸）：CHAR_WANG_MOTHER↔CHAR_SHI_TAIGONG（同主色「白」）——用互斥发色/服装主色/配饰强分，必要时拆反打。 | identity | 按处方补该角色缺的视图/表情/服装参考并重建出图包。 |
| warn | same_frame_color_collision | 生产数据/comic_reference_plan_第6话.json | P034 多人同框主色撞色（易串脸）：CHAR_WANG_JIN↔CHAR_WANG_MOTHER（同主色「白」）、CHAR_WANG_JIN↔CHAR_SHI_TAIGONG（同主色「白」）、CHAR_WANG_MOTHER↔CHAR_SHI_TAIGONG（同主色「白」）——用互斥发色/服装主色/配饰强分，必要时拆反打。 | identity | 按处方补该角色缺的视图/表情/服装参考并重建出图包。 |
| warn | same_frame_color_collision | 生产数据/comic_reference_plan_第6话.json | P035 多人同框主色撞色（易串脸）：CHAR_WANG_JIN↔CHAR_WANG_MOTHER（同主色「白」）——用互斥发色/服装主色/配饰强分，必要时拆反打。 | identity | 按处方补该角色缺的视图/表情/服装参考并重建出图包。 |
| warn | same_frame_color_collision | 生产数据/comic_reference_plan_第6话.json | P037 多人同框主色撞色（易串脸）：CHAR_WANG_JIN↔CHAR_WANG_MOTHER（同主色「白」）——用互斥发色/服装主色/配饰强分，必要时拆反打。 | identity | 按处方补该角色缺的视图/表情/服装参考并重建出图包。 |
| warn | same_frame_color_collision | 生产数据/comic_reference_plan_第6话.json | P038 多人同框主色撞色（易串脸）：CHAR_WANG_JIN↔CHAR_WANG_MOTHER（同主色「白」）——用互斥发色/服装主色/配饰强分，必要时拆反打。 | identity | 按处方补该角色缺的视图/表情/服装参考并重建出图包。 |
| info | panel_post_qc_warn | 出图/第6话/panels/P034.png | P034 的落盘 post_qc=warn 已人审签收为误报：人工复核确认候选白区为院门外自然雾天空景，不是预烘焙气泡或文字容器；画面无文字，构图与剧情可用。 | review | 若该格重抽或构图变化，需要重新复核 panel_qc。 |
| info | panel_post_qc_warn | 出图/第6话/panels/P047.png | P047 的落盘 post_qc=warn 已人审签收为误报：人工复核确认候选白区为史进白色孝服衣袖高光，不是预烘焙气泡或文字容器；画面无文字，构图与剧情可用。 | review | 若该格重抽或构图变化，需要重新复核 panel_qc。 |
| warn | panel_style_outlier | 出图/第6话/panels/P010.png | 风格指纹内聚度 0.7150 明显低于本话中位 0.7932，疑似画风、细节密度或照片感跳变。 | image | 与全话 contact sheet 并排人审；若确实跳变，回 comic-image 用同一风格锚和参考图重抽该格。 |
| warn | panel_style_outlier | 出图/第6话/panels/P013.png | 风格指纹内聚度 0.6565 明显低于本话中位 0.7932，疑似画风、细节密度或照片感跳变。 | image | 与全话 contact sheet 并排人审；若确实跳变，回 comic-image 用同一风格锚和参考图重抽该格。 |
| warn | panel_style_outlier | 出图/第6话/panels/P018.png | 风格指纹内聚度 0.7447 明显低于本话中位 0.7932，疑似画风、细节密度或照片感跳变。 | image | 与全话 contact sheet 并排人审；若确实跳变，回 comic-image 用同一风格锚和参考图重抽该格。 |
| warn | panel_style_outlier | 出图/第6话/panels/P023.png | 风格指纹内聚度 0.6960 明显低于本话中位 0.7932，疑似画风、细节密度或照片感跳变。 | image | 与全话 contact sheet 并排人审；若确实跳变，回 comic-image 用同一风格锚和参考图重抽该格。 |
| warn | panel_style_outlier | 出图/第6话/panels/P024.png | 风格指纹内聚度 0.4681 明显低于本话中位 0.7932，疑似画风、细节密度或照片感跳变。 | image | 与全话 contact sheet 并排人审；若确实跳变，回 comic-image 用同一风格锚和参考图重抽该格。 |
| warn | panel_style_outlier | 出图/第6话/panels/P026.png | 风格指纹内聚度 0.4121 明显低于本话中位 0.7932，疑似画风、细节密度或照片感跳变。 | image | 与全话 contact sheet 并排人审；若确实跳变，回 comic-image 用同一风格锚和参考图重抽该格。 |
| warn | panel_style_outlier | 出图/第6话/panels/P029.png | 风格指纹内聚度 0.5815 明显低于本话中位 0.7932，疑似画风、细节密度或照片感跳变。 | image | 与全话 contact sheet 并排人审；若确实跳变，回 comic-image 用同一风格锚和参考图重抽该格。 |
| warn | panel_style_outlier | 出图/第6话/panels/P031.png | 风格指纹内聚度 0.7107 明显低于本话中位 0.7932，疑似画风、细节密度或照片感跳变。 | image | 与全话 contact sheet 并排人审；若确实跳变，回 comic-image 用同一风格锚和参考图重抽该格。 |
| warn | panel_style_outlier | 出图/第6话/panels/P032.png | 风格指纹内聚度 0.6544 明显低于本话中位 0.7932，疑似画风、细节密度或照片感跳变。 | image | 与全话 contact sheet 并排人审；若确实跳变，回 comic-image 用同一风格锚和参考图重抽该格。 |
| warn | panel_style_outlier | 出图/第6话/panels/P036.png | 风格指纹内聚度 0.7207 明显低于本话中位 0.7932，疑似画风、细节密度或照片感跳变。 | image | 与全话 contact sheet 并排人审；若确实跳变，回 comic-image 用同一风格锚和参考图重抽该格。 |
| warn | panel_style_outlier | 出图/第6话/panels/P040.png | 风格指纹内聚度 0.6858 明显低于本话中位 0.7932，疑似画风、细节密度或照片感跳变。 | image | 与全话 contact sheet 并排人审；若确实跳变，回 comic-image 用同一风格锚和参考图重抽该格。 |
| warn | panel_style_outlier | 出图/第6话/panels/P042.png | 风格指纹内聚度 0.6181 明显低于本话中位 0.7932，疑似画风、细节密度或照片感跳变。 | image | 与全话 contact sheet 并排人审；若确实跳变，回 comic-image 用同一风格锚和参考图重抽该格。 |
| warn | panel_style_outlier | 出图/第6话/panels/P048.png | 风格指纹内聚度 0.7203 明显低于本话中位 0.7932，疑似画风、细节密度或照片感跳变。 | image | 与全话 contact sheet 并排人审；若确实跳变，回 comic-image 用同一风格锚和参考图重抽该格。 |
| warn | location_color_grade_shift | 出图/第6话/panels/P024.png | 同场景“LOC_SHI_MANOR”内调色代理偏离组中位：warmth_dev=0.405, tint_dev=0.000。 | image | 人审确认是否为有意光效；否则统一白平衡/冷暖光口径后重抽该格。 |
| warn | location_color_grade_shift | 出图/第6话/panels/P026.png | 同场景“LOC_SHI_MANOR”内调色代理偏离组中位：warmth_dev=0.553, tint_dev=0.041。 | image | 人审确认是否为有意光效；否则统一白平衡/冷暖光口径后重抽该格。 |
| warn | location_color_grade_shift | 出图/第6话/panels/P013.png | 同场景“LOC_SHI_TRAINING_YARD”内调色代理偏离组中位：warmth_dev=0.255, tint_dev=0.024。 | image | 人审确认是否为有意光效；否则统一白平衡/冷暖光口径后重抽该格。 |
| warn | adjacent_panel_grade_jump | 出图/第6话/panels/P024.png | 与同场景锚 LOC_SHI_MANOR 的前一格 P023 相比冷暖/亮度跳变：warmth_jump=0.415, val_jump=0.005；疑似光位翻转或昼夜漂移。 | image | 并排两格人审；非剧情光效则按场景锚 lighting_anchor 重抽该格。 |
| warn | adjacent_panel_grade_jump | 出图/第6话/panels/P025.png | 与同场景锚 LOC_SHI_MANOR 的前一格 P024 相比冷暖/亮度跳变：warmth_jump=0.452, val_jump=0.089；疑似光位翻转或昼夜漂移。 | image | 并排两格人审；非剧情光效则按场景锚 lighting_anchor 重抽该格。 |
| warn | adjacent_panel_grade_jump | 出图/第6话/panels/P026.png | 与同场景锚 LOC_SHI_MANOR 的前一格 P025 相比冷暖/亮度跳变：warmth_jump=0.600, val_jump=0.053；疑似光位翻转或昼夜漂移。 | image | 并排两格人审；非剧情光效则按场景锚 lighting_anchor 重抽该格。 |
| warn | adjacent_panel_grade_jump | 出图/第6话/panels/P027.png | 与同场景锚 LOC_SHI_MANOR 的前一格 P026 相比冷暖/亮度跳变：warmth_jump=0.623, val_jump=0.138；疑似光位翻转或昼夜漂移。 | image | 并排两格人审；非剧情光效则按场景锚 lighting_anchor 重抽该格。 |
| warn | adjacent_panel_grade_jump | 出图/第6话/panels/P031.png | 与同场景锚 LOC_SHI_MANOR 的前一格 P030 相比冷暖/亮度跳变：warmth_jump=0.126, val_jump=0.365；疑似光位翻转或昼夜漂移。 | image | 并排两格人审；非剧情光效则按场景锚 lighting_anchor 重抽该格。 |
| warn | adjacent_panel_grade_jump | 出图/第6话/panels/P040.png | 与同场景锚 LOC_SHI_TRAINING_YARD 的前一格 P039 相比冷暖/亮度跳变：warmth_jump=0.215, val_jump=0.355；疑似光位翻转或昼夜漂移。 | image | 并排两格人审；非剧情光效则按场景锚 lighting_anchor 重抽该格。 |
| warn | adjacent_panel_grade_jump | 出图/第6话/panels/P041.png | 与同场景锚 LOC_SHI_TRAINING_YARD 的前一格 P040 相比冷暖/亮度跳变：warmth_jump=0.169, val_jump=0.357；疑似光位翻转或昼夜漂移。 | image | 并排两格人审；非剧情光效则按场景锚 lighting_anchor 重抽该格。 |
| warn | tone_value_outlier | 出图/第6话/panels/P002.png | 黑白灰量化偏离话内中位：black_ratio=0.337（中位 0.037），线宽代理 edge_density=0.1035（中位 0.126）。疑似网点密度/黑场/线宽口径不统一。 | image | 对照 finishing_plan 的 tone/black/ink 计划人审；口径确实漂了则统一收尾契约后重抽。 |
| warn | tone_value_outlier | 出图/第6话/panels/P010.png | 黑白灰量化偏离话内中位：black_ratio=0.3873（中位 0.037），线宽代理 edge_density=0.0959（中位 0.126）。疑似网点密度/黑场/线宽口径不统一。 | image | 对照 finishing_plan 的 tone/black/ink 计划人审；口径确实漂了则统一收尾契约后重抽。 |
| warn | tone_value_outlier | 出图/第6话/panels/P017.png | 黑白灰量化偏离话内中位：black_ratio=0.3099（中位 0.037），线宽代理 edge_density=0.1126（中位 0.126）。疑似网点密度/黑场/线宽口径不统一。 | image | 对照 finishing_plan 的 tone/black/ink 计划人审；口径确实漂了则统一收尾契约后重抽。 |
| warn | tone_value_outlier | 出图/第6话/panels/P022.png | 黑白灰量化偏离话内中位：black_ratio=0.3191（中位 0.037），线宽代理 edge_density=0.0977（中位 0.126）。疑似网点密度/黑场/线宽口径不统一。 | image | 对照 finishing_plan 的 tone/black/ink 计划人审；口径确实漂了则统一收尾契约后重抽。 |
| warn | tone_value_outlier | 出图/第6话/panels/P023.png | 黑白灰量化偏离话内中位：black_ratio=0.4405（中位 0.037），线宽代理 edge_density=0.0629（中位 0.126）。疑似网点密度/黑场/线宽口径不统一。 | image | 对照 finishing_plan 的 tone/black/ink 计划人审；口径确实漂了则统一收尾契约后重抽。 |
| warn | tone_value_outlier | 出图/第6话/panels/P024.png | 黑白灰量化偏离话内中位：black_ratio=0.2396（中位 0.037），线宽代理 edge_density=0.0565（中位 0.126）。疑似网点密度/黑场/线宽口径不统一。 | image | 对照 finishing_plan 的 tone/black/ink 计划人审；口径确实漂了则统一收尾契约后重抽。 |
| warn | tone_value_outlier | 出图/第6话/panels/P031.png | 黑白灰量化偏离话内中位：black_ratio=0.3345（中位 0.037），线宽代理 edge_density=0.0724（中位 0.126）。疑似网点密度/黑场/线宽口径不统一。 | image | 对照 finishing_plan 的 tone/black/ink 计划人审；口径确实漂了则统一收尾契约后重抽。 |
| warn | tone_value_outlier | 出图/第6话/panels/P040.png | 黑白灰量化偏离话内中位：black_ratio=0.3793（中位 0.037），线宽代理 edge_density=0.099（中位 0.126）。疑似网点密度/黑场/线宽口径不统一。 | image | 对照 finishing_plan 的 tone/black/ink 计划人审；口径确实漂了则统一收尾契约后重抽。 |
| warn | style_anchor_drift | 出图/共享/style_baseline.json | 本话整体指纹与风格锚图最高相似度仅 0.8762，风格锚可能已失去约束力。 | image | 并排比对锚图与本话 contact sheet；必要时更新风格锚或统一重抽。 |
| warn | hair_fingerprint_low | 出图/第6话/panels/P002.png | CHAR_SHI_JIN hair 指纹与参考图相似度偏低：score=0.451。这是色彩分布代理，需并排人审。 | image | 查看 character consistency contact sheet；如确实换脸/换发型/换服装，回 comic-image 用同一参考组重抽该格。 |
| warn | hair_fingerprint_low | 出图/第6话/panels/P010.png | CHAR_SHI_JIN hair 指纹与参考图相似度偏低：score=0.448。这是色彩分布代理，需并排人审。 | image | 查看 character consistency contact sheet；如确实换脸/换发型/换服装，回 comic-image 用同一参考组重抽该格。 |
| warn | hair_fingerprint_low | 出图/第6话/panels/P017.png | CHAR_SHI_JIN hair 指纹与参考图相似度偏低：score=0.391。这是色彩分布代理，需并排人审。 | image | 查看 character consistency contact sheet；如确实换脸/换发型/换服装，回 comic-image 用同一参考组重抽该格。 |
| warn | hair_fingerprint_low | 出图/第6话/panels/P018.png | CHAR_SHI_JIN hair 指纹与参考图相似度偏低：score=0.423。这是色彩分布代理，需并排人审。 | image | 查看 character consistency contact sheet；如确实换脸/换发型/换服装，回 comic-image 用同一参考组重抽该格。 |
| warn | hair_fingerprint_low | 出图/第6话/panels/P031.png | CHAR_SHI_JIN hair 指纹与参考图相似度偏低：score=0.317。这是色彩分布代理，需并排人审。 | image | 查看 character consistency contact sheet；如确实换脸/换发型/换服装，回 comic-image 用同一参考组重抽该格。 |
| warn | face_fingerprint_low | 出图/第6话/panels/P032.png | CHAR_SHI_JIN face 指纹与参考图相似度偏低：score=0.452。这是色彩分布代理，需并排人审。 | image | 查看 character consistency contact sheet；如确实换脸/换发型/换服装，回 comic-image 用同一参考组重抽该格。 |
| warn | hair_fingerprint_low | 出图/第6话/panels/P032.png | CHAR_SHI_JIN hair 指纹与参考图相似度偏低：score=0.210。这是色彩分布代理，需并排人审。 | image | 查看 character consistency contact sheet；如确实换脸/换发型/换服装，回 comic-image 用同一参考组重抽该格。 |
| warn | face_fingerprint_low | 出图/第6话/panels/P040.png | CHAR_SHI_JIN face 指纹与参考图相似度偏低：score=0.392。这是色彩分布代理，需并排人审。 | image | 查看 character consistency contact sheet；如确实换脸/换发型/换服装，回 comic-image 用同一参考组重抽该格。 |
| warn | hair_fingerprint_low | 出图/第6话/panels/P040.png | CHAR_SHI_JIN hair 指纹与参考图相似度偏低：score=0.248。这是色彩分布代理，需并排人审。 | image | 查看 character consistency contact sheet；如确实换脸/换发型/换服装，回 comic-image 用同一参考组重抽该格。 |
| warn | outfit_fingerprint_low | 出图/第6话/panels/P003.png | CHAR_SHI_TAIGONG outfit 指纹与参考图相似度偏低：score=0.328。这是色彩分布代理，需并排人审。 | image | 查看 character consistency contact sheet；如确实换脸/换发型/换服装，回 comic-image 用同一参考组重抽该格。 |
| warn | outfit_fingerprint_low | 出图/第6话/panels/P005.png | CHAR_SHI_TAIGONG outfit 指纹与参考图相似度偏低：score=0.330。这是色彩分布代理，需并排人审。 | image | 查看 character consistency contact sheet；如确实换脸/换发型/换服装，回 comic-image 用同一参考组重抽该格。 |
| warn | face_fingerprint_low | 出图/第6话/panels/P029.png | CHAR_SHI_TAIGONG face 指纹与参考图相似度偏低：score=0.471。这是色彩分布代理，需并排人审。 | image | 查看 character consistency contact sheet；如确实换脸/换发型/换服装，回 comic-image 用同一参考组重抽该格。 |
| warn | hair_fingerprint_low | 出图/第6话/panels/P029.png | CHAR_SHI_TAIGONG hair 指纹与参考图相似度偏低：score=0.255。这是色彩分布代理，需并排人审。 | image | 查看 character consistency contact sheet；如确实换脸/换发型/换服装，回 comic-image 用同一参考组重抽该格。 |
| warn | outfit_fingerprint_low | 出图/第6话/panels/P029.png | CHAR_SHI_TAIGONG outfit 指纹与参考图相似度偏低：score=0.221。这是色彩分布代理，需并排人审。 | image | 查看 character consistency contact sheet；如确实换脸/换发型/换服装，回 comic-image 用同一参考组重抽该格。 |
| warn | hair_fingerprint_low | 出图/第6话/panels/P033.png | CHAR_SHI_TAIGONG hair 指纹与参考图相似度偏低：score=0.436。这是色彩分布代理，需并排人审。 | image | 查看 character consistency contact sheet；如确实换脸/换发型/换服装，回 comic-image 用同一参考组重抽该格。 |
| warn | outfit_fingerprint_low | 出图/第6话/panels/P033.png | CHAR_SHI_TAIGONG outfit 指纹与参考图相似度偏低：score=0.335。这是色彩分布代理，需并排人审。 | image | 查看 character consistency contact sheet；如确实换脸/换发型/换服装，回 comic-image 用同一参考组重抽该格。 |
| warn | hair_fingerprint_low | 出图/第6话/panels/P042.png | CHAR_SHI_TAIGONG hair 指纹与参考图相似度偏低：score=0.443。这是色彩分布代理，需并排人审。 | image | 查看 character consistency contact sheet；如确实换脸/换发型/换服装，回 comic-image 用同一参考组重抽该格。 |
| warn | hair_fingerprint_low | 出图/第6话/panels/P044.png | CHAR_SHI_TAIGONG hair 指纹与参考图相似度偏低：score=0.412。这是色彩分布代理，需并排人审。 | image | 查看 character consistency contact sheet；如确实换脸/换发型/换服装，回 comic-image 用同一参考组重抽该格。 |
| warn | outfit_fingerprint_low | 出图/第6话/panels/P044.png | CHAR_SHI_TAIGONG outfit 指纹与参考图相似度偏低：score=0.417。这是色彩分布代理，需并排人审。 | image | 查看 character consistency contact sheet；如确实换脸/换发型/换服装，回 comic-image 用同一参考组重抽该格。 |
| warn | hair_fingerprint_low | 出图/第6话/panels/P002.png | CHAR_WANG_JIN hair 指纹与参考图相似度偏低：score=0.305。这是色彩分布代理，需并排人审。 | image | 查看 character consistency contact sheet；如确实换脸/换发型/换服装，回 comic-image 用同一参考组重抽该格。 |
| warn | hair_fingerprint_low | 出图/第6话/panels/P010.png | CHAR_WANG_JIN hair 指纹与参考图相似度偏低：score=0.434。这是色彩分布代理，需并排人审。 | image | 查看 character consistency contact sheet；如确实换脸/换发型/换服装，回 comic-image 用同一参考组重抽该格。 |
| warn | hair_fingerprint_low | 出图/第6话/panels/P016.png | CHAR_WANG_JIN hair 指纹与参考图相似度偏低：score=0.451。这是色彩分布代理，需并排人审。 | image | 查看 character consistency contact sheet；如确实换脸/换发型/换服装，回 comic-image 用同一参考组重抽该格。 |
| warn | hair_fingerprint_low | 出图/第6话/panels/P017.png | CHAR_WANG_JIN hair 指纹与参考图相似度偏低：score=0.295。这是色彩分布代理，需并排人审。 | image | 查看 character consistency contact sheet；如确实换脸/换发型/换服装，回 comic-image 用同一参考组重抽该格。 |
| warn | face_fingerprint_low | 出图/第6话/panels/P018.png | CHAR_WANG_JIN face 指纹与参考图相似度偏低：score=0.491。这是色彩分布代理，需并排人审。 | image | 查看 character consistency contact sheet；如确实换脸/换发型/换服装，回 comic-image 用同一参考组重抽该格。 |
| warn | hair_fingerprint_low | 出图/第6话/panels/P018.png | CHAR_WANG_JIN hair 指纹与参考图相似度偏低：score=0.339。这是色彩分布代理，需并排人审。 | image | 查看 character consistency contact sheet；如确实换脸/换发型/换服装，回 comic-image 用同一参考组重抽该格。 |
| warn | outfit_fingerprint_low | 出图/第6话/panels/P023.png | CHAR_WANG_JIN outfit 指纹与参考图相似度偏低：score=0.418。这是色彩分布代理，需并排人审。 | image | 查看 character consistency contact sheet；如确实换脸/换发型/换服装，回 comic-image 用同一参考组重抽该格。 |
| warn | face_fingerprint_low | 出图/第6话/panels/P024.png | CHAR_WANG_JIN face 指纹与参考图相似度偏低：score=0.480。这是色彩分布代理，需并排人审。 | image | 查看 character consistency contact sheet；如确实换脸/换发型/换服装，回 comic-image 用同一参考组重抽该格。 |
| warn | hair_fingerprint_low | 出图/第6话/panels/P024.png | CHAR_WANG_JIN hair 指纹与参考图相似度偏低：score=0.422。这是色彩分布代理，需并排人审。 | image | 查看 character consistency contact sheet；如确实换脸/换发型/换服装，回 comic-image 用同一参考组重抽该格。 |
| warn | face_fingerprint_low | 出图/第6话/panels/P026.png | CHAR_WANG_JIN face 指纹与参考图相似度偏低：score=0.433。这是色彩分布代理，需并排人审。 | image | 查看 character consistency contact sheet；如确实换脸/换发型/换服装，回 comic-image 用同一参考组重抽该格。 |
| warn | hair_fingerprint_low | 出图/第6话/panels/P026.png | CHAR_WANG_JIN hair 指纹与参考图相似度偏低：score=0.427。这是色彩分布代理，需并排人审。 | image | 查看 character consistency contact sheet；如确实换脸/换发型/换服装，回 comic-image 用同一参考组重抽该格。 |
| warn | outfit_fingerprint_low | 出图/第6话/panels/P026.png | CHAR_WANG_JIN outfit 指纹与参考图相似度偏低：score=0.334。这是色彩分布代理，需并排人审。 | image | 查看 character consistency contact sheet；如确实换脸/换发型/换服装，回 comic-image 用同一参考组重抽该格。 |
| warn | face_fingerprint_low | 出图/第6话/panels/P029.png | CHAR_WANG_JIN face 指纹与参考图相似度偏低：score=0.401。这是色彩分布代理，需并排人审。 | image | 查看 character consistency contact sheet；如确实换脸/换发型/换服装，回 comic-image 用同一参考组重抽该格。 |
| warn | hair_fingerprint_low | 出图/第6话/panels/P029.png | CHAR_WANG_JIN hair 指纹与参考图相似度偏低：score=0.436。这是色彩分布代理，需并排人审。 | image | 查看 character consistency contact sheet；如确实换脸/换发型/换服装，回 comic-image 用同一参考组重抽该格。 |
| warn | hair_fingerprint_low | 出图/第6话/panels/P031.png | CHAR_WANG_JIN hair 指纹与参考图相似度偏低：score=0.319。这是色彩分布代理，需并排人审。 | image | 查看 character consistency contact sheet；如确实换脸/换发型/换服装，回 comic-image 用同一参考组重抽该格。 |
| warn | face_fingerprint_low | 出图/第6话/panels/P032.png | CHAR_WANG_JIN face 指纹与参考图相似度偏低：score=0.364。这是色彩分布代理，需并排人审。 | image | 查看 character consistency contact sheet；如确实换脸/换发型/换服装，回 comic-image 用同一参考组重抽该格。 |
| warn | hair_fingerprint_low | 出图/第6话/panels/P032.png | CHAR_WANG_JIN hair 指纹与参考图相似度偏低：score=0.189。这是色彩分布代理，需并排人审。 | image | 查看 character consistency contact sheet；如确实换脸/换发型/换服装，回 comic-image 用同一参考组重抽该格。 |
| warn | outfit_fingerprint_low | 出图/第6话/panels/P038.png | CHAR_WANG_JIN outfit 指纹与参考图相似度偏低：score=0.365。这是色彩分布代理，需并排人审。 | image | 查看 character consistency contact sheet；如确实换脸/换发型/换服装，回 comic-image 用同一参考组重抽该格。 |
| warn | identity_similarity_engine_degraded | 生产数据/comic_character_consistency_第6话.json | CCIP 动漫身份 embedding 不可用，角色/生物相似度机检降级为色彩分布代理（同色调换脸/变形会漏报）。 | review | 独立 venv 安装 dghs-imgutils 后重跑 gate；在装好前必须以 VLM 并排裁决兜底身份轴。 |
| warn | vlm_judge_unadjudicated | 生产数据/comic_vlm_judge_tasks_第6话.json | VLM 并排判定任务包已生成 130 条但 0 条裁决——角色/生物身份、背景、道具三轴机检空转，画错生物形态这类漂移不会被拦。 | review | 由多模态 agent 逐条看图打分并写回 生产数据/comic_vlm_judge_verdicts_第6话.json 后重跑 gate。 |
