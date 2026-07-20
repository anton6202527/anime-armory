# 漫画 Gate — review — 第8话

- 生成时间：2026-07-20T15:04:24
- 结论：warn
- block/warn/info：0 / 117 / 12

## 记录

- 开发包严格合同: pass
- 源范围/SHA/逐格 coverage 合同: pass
- continuity_audit: chapters=8 block=0 warn=0
- 缩略分镜/name board 审批合同: pass
- 排版审批合同: pass
- 原稿收尾合同: pass
- backend adapter: dreamina_image2image; reference_image_limit=10; persistent_subject=False
- 角色注册表 v2: pass
- 角色多视图技术齐套与人审签收: pass
- chapter_beat_audit: must=0 warn=2（advisory·不阻断）
- setup_payoff_ledger: must=0 warn=0（advisory·不阻断）
- reentry_context_audit: must=0 warn=0（advisory·不阻断）
- entity_presence_audit: must=0 warn=4（advisory·不阻断）
- redundancy_audit: must=0 warn=0（advisory·不阻断）
- subtext_audit: must=0 warn=0（advisory·不阻断）
- reference_planner: 含角色格 45 需处理 19；处方 SHA 已校验
- panel_variety: panels=48 近重复对=1（advisory·不阻断）
- style consistency refreshed: 生产数据/comic_style_consistency_第8话.md
- character consistency refreshed: 生产数据/comic_character_consistency_第8话.md
- scene/prop consistency refreshed: 生产数据/comic_scene_prop_consistency_第8话.md
- comic-review report refreshed in review gate
- drift_report: 追踪 24 角色 · 有漂移 8（跨话汇总·advisory）

## Findings

| severity | code | artifact | reason | return_to | suggested_fix |
|---|---|---|---|---|---|
| warn | ending_mode_mismatch | 生产数据/comic_chapter_beat_audit_第8话.json | 合同 ending_mode=cliffhanger，末格 story_function=ending_promise；期望候选为 ['cliffhanger', 'hook']。这是编辑复核提示，不是硬闸。 | comic-script | 按机检建议回 comic-script 修分话/分格后重跑。 |
| warn | no_climax_panel | 生产数据/comic_chapter_beat_audit_第8话.json | 未标出高潮/转折/兑现格；请人工确认节拍不是平推。 | comic-script | 按机检建议回 comic-script 修分话/分格后重跑。 |
| warn | mentioned_not_bound | 生产数据/comic_entity_presence_audit_第8话.json | P025 画面描述提到「朱武」（registry 实体 CHAR_ZHU_WU），但该格 characters/references/scene_anchor 都没绑它——出图不会附其定妆参考，形态全靠模型自由发挥。确认入画则补进该格 references（或 characters），不入画则改写描述。 | comic-script | 按机检建议回 comic-script 修分话/分格后重跑。 |
| warn | mentioned_not_bound | 生产数据/comic_entity_presence_audit_第8话.json | P025 画面描述提到「陈达」（registry 实体 CHAR_CHEN_DA），但该格 characters/references/scene_anchor 都没绑它——出图不会附其定妆参考，形态全靠模型自由发挥。确认入画则补进该格 references（或 characters），不入画则改写描述。 | comic-script | 按机检建议回 comic-script 修分话/分格后重跑。 |
| warn | mentioned_not_bound | 生产数据/comic_entity_presence_audit_第8话.json | P025 画面描述提到「杨春」（registry 实体 CHAR_YANG_CHUN），但该格 characters/references/scene_anchor 都没绑它——出图不会附其定妆参考，形态全靠模型自由发挥。确认入画则补进该格 references（或 characters），不入画则改写描述。 | comic-script | 按机检建议回 comic-script 修分话/分格后重跑。 |
| warn | mentioned_not_bound | 生产数据/comic_entity_presence_audit_第8话.json | P027 画面描述提到「王四」（registry 实体 CHAR_WANG_SI），但该格 characters/references/scene_anchor 都没绑它——出图不会附其定妆参考，形态全靠模型自由发挥。确认入画则补进该格 references（或 characters），不入画则改写描述。 | comic-script | 按机检建议回 comic-script 修分话/分格后重跑。 |
| warn | same_frame_color_collision | 生产数据/comic_reference_plan_第8话.json | P011 多人同框主色撞色（易串脸）：CHAR_ZHU_WU↔CHAR_CHEN_DA（同主色「红」）——用互斥发色/服装主色/配饰强分，必要时拆反打。 | identity | 按处方补该角色缺的视图/表情/服装参考并重建出图包。 |
| warn | same_frame_color_collision | 生产数据/comic_reference_plan_第8话.json | P016 多人同框主色撞色（易串脸）：CHAR_ZHU_WU↔CHAR_CHEN_DA（同主色「红」）——用互斥发色/服装主色/配饰强分，必要时拆反打。 | identity | 按处方补该角色缺的视图/表情/服装参考并重建出图包。 |
| warn | missing_reference | 生产数据/comic_reference_plan_第8话.json | P021·王四：缺 45°/three_quarter 参考（档位或本格变化量需要） | identity | 按处方补该角色缺的视图/表情/服装参考并重建出图包。 |
| warn | missing_reference | 生产数据/comic_reference_plan_第8话.json | P021·王四：缺 45°/¾ 侧脸参考（动作格主身份锚·避免 frontal 摆拍偏置） | identity | 按处方补该角色缺的视图/表情/服装参考并重建出图包。 |
| warn | same_frame_color_collision | 生产数据/comic_reference_plan_第8话.json | P028 多人同框主色撞色（易串脸）：CHAR_LI_JI↔CHAR_COUNTY_LIEUTENANT（同主色「黑」）——用互斥发色/服装主色/配饰强分，必要时拆反打。 | identity | 按处方补该角色缺的视图/表情/服装参考并重建出图包。 |
| warn | missing_reference | 生产数据/comic_reference_plan_第8话.json | P034·王四：缺 45°/three_quarter 参考（档位或本格变化量需要） | identity | 按处方补该角色缺的视图/表情/服装参考并重建出图包。 |
| warn | missing_reference | 生产数据/comic_reference_plan_第8话.json | P034·王四：缺 45°/¾ 侧脸参考（动作格主身份锚·避免 frontal 摆拍偏置） | identity | 按处方补该角色缺的视图/表情/服装参考并重建出图包。 |
| warn | same_frame_color_collision | 生产数据/comic_reference_plan_第8话.json | P038 多人同框主色撞色（易串脸）：CHAR_ZHU_WU↔CHAR_CHEN_DA（同主色「红」）——用互斥发色/服装主色/配饰强分，必要时拆反打。 | identity | 按处方补该角色缺的视图/表情/服装参考并重建出图包。 |
| warn | same_frame_color_collision | 生产数据/comic_reference_plan_第8话.json | P039 多人同框主色撞色（易串脸）：CHAR_ZHU_WU↔CHAR_CHEN_DA（同主色「红」）——用互斥发色/服装主色/配饰强分，必要时拆反打。 | identity | 按处方补该角色缺的视图/表情/服装参考并重建出图包。 |
| warn | same_frame_color_collision | 生产数据/comic_reference_plan_第8话.json | P040 多人同框主色撞色（易串脸）：CHAR_ZHU_WU↔CHAR_CHEN_DA（同主色「红」）——用互斥发色/服装主色/配饰强分，必要时拆反打。 | identity | 按处方补该角色缺的视图/表情/服装参考并重建出图包。 |
| warn | same_frame_color_collision | 生产数据/comic_reference_plan_第8话.json | P042 多人同框主色撞色（易串脸）：CHAR_ZHU_WU↔CHAR_CHEN_DA（同主色「红」）——用互斥发色/服装主色/配饰强分，必要时拆反打。 | identity | 按处方补该角色缺的视图/表情/服装参考并重建出图包。 |
| warn | same_frame_color_collision | 生产数据/comic_reference_plan_第8话.json | P044 多人同框主色撞色（易串脸）：CHAR_ZHU_WU↔CHAR_CHEN_DA（同主色「红」）——用互斥发色/服装主色/配饰强分，必要时拆反打。 | identity | 按处方补该角色缺的视图/表情/服装参考并重建出图包。 |
| warn | same_frame_color_collision | 生产数据/comic_reference_plan_第8话.json | P046 多人同框主色撞色（易串脸）：CHAR_SHI_JIN↔CHAR_COUNTY_LIEUTENANT（同主色「黑」）——用互斥发色/服装主色/配饰强分，必要时拆反打。 | identity | 按处方补该角色缺的视图/表情/服装参考并重建出图包。 |
| warn | missing_reference | 生产数据/comic_reference_plan_第8话.json | P048·史进：缺 全身/三视图参考（远景/全身动作格·单张头肩定妆不够） | identity | 按处方补该角色缺的视图/表情/服装参考并重建出图包。 |
| warn | missing_reference | 生产数据/comic_reference_plan_第8话.json | P048·朱武：缺 全身/三视图参考（远景/全身动作格·单张头肩定妆不够） | identity | 按处方补该角色缺的视图/表情/服装参考并重建出图包。 |
| warn | missing_reference | 生产数据/comic_reference_plan_第8话.json | P048·陈达：缺 全身/三视图参考（远景/全身动作格·单张头肩定妆不够） | identity | 按处方补该角色缺的视图/表情/服装参考并重建出图包。 |
| warn | missing_reference | 生产数据/comic_reference_plan_第8话.json | P048·杨春：缺 全身/三视图参考（远景/全身动作格·单张头肩定妆不够） | identity | 按处方补该角色缺的视图/表情/服装参考并重建出图包。 |
| warn | same_frame_color_collision | 生产数据/comic_reference_plan_第8话.json | P048 多人同框主色撞色（易串脸）：CHAR_ZHU_WU↔CHAR_CHEN_DA（同主色「红」）——用互斥发色/服装主色/配饰强分，必要时拆反打。 | identity | 按处方补该角色缺的视图/表情/服装参考并重建出图包。 |
| info | panel_post_qc_warn | 出图/第8话/panels/P018.png | P018 的落盘 post_qc=warn 已人审签收为误报：人工复核确认候选白区为山雾与天空自然留白，不是预烘焙气泡或文字容器；画面无文字，人物动作与场景可用。 | review | 若该格重抽或构图变化，需要重新复核 panel_qc。 |
| info | panel_post_qc_warn | 出图/第8话/panels/P033.png | P033 的落盘 post_qc=warn 已人审签收为误报：人工复核确认候选白区为晨昏天空自然留白，不是预烘焙气泡或文字容器；画面无文字，人物动作与场景可用。 | review | 若该格重抽或构图变化，需要重新复核 panel_qc。 |
| warn | near_duplicate_panels | 生产数据/comic_panel_variety_第8话.json | P026 ↔ P032 构图近重复（dHash=8/64·非相邻格）——一屏多格时重复构图立刻穿帮；换景别/机位/前景遮挡重出其一，或合并格。 | comic-image | 换景别/机位/前景遮挡重出其一，或回 comic-script 合并格。 |
| warn | panel_style_outlier | 出图/第8话/panels/P001.png | 风格指纹内聚度 0.5622 明显低于本话中位 0.8076，疑似画风、细节密度或照片感跳变。 | image | 与全话 contact sheet 并排人审；若确实跳变，回 comic-image 用同一风格锚和参考图重抽该格。 |
| warn | panel_style_outlier | 出图/第8话/panels/P002.png | 风格指纹内聚度 0.7573 明显低于本话中位 0.8076，疑似画风、细节密度或照片感跳变。 | image | 与全话 contact sheet 并排人审；若确实跳变，回 comic-image 用同一风格锚和参考图重抽该格。 |
| warn | panel_style_outlier | 出图/第8话/panels/P004.png | 风格指纹内聚度 0.7321 明显低于本话中位 0.8076，疑似画风、细节密度或照片感跳变。 | image | 与全话 contact sheet 并排人审；若确实跳变，回 comic-image 用同一风格锚和参考图重抽该格。 |
| warn | panel_style_outlier | 出图/第8话/panels/P005.png | 风格指纹内聚度 0.7185 明显低于本话中位 0.8076，疑似画风、细节密度或照片感跳变。 | image | 与全话 contact sheet 并排人审；若确实跳变，回 comic-image 用同一风格锚和参考图重抽该格。 |
| warn | panel_style_outlier | 出图/第8话/panels/P007.png | 风格指纹内聚度 0.7342 明显低于本话中位 0.8076，疑似画风、细节密度或照片感跳变。 | image | 与全话 contact sheet 并排人审；若确实跳变，回 comic-image 用同一风格锚和参考图重抽该格。 |
| warn | panel_style_outlier | 出图/第8话/panels/P008.png | 风格指纹内聚度 0.6897 明显低于本话中位 0.8076，疑似画风、细节密度或照片感跳变。 | image | 与全话 contact sheet 并排人审；若确实跳变，回 comic-image 用同一风格锚和参考图重抽该格。 |
| warn | panel_style_outlier | 出图/第8话/panels/P018.png | 风格指纹内聚度 0.7386 明显低于本话中位 0.8076，疑似画风、细节密度或照片感跳变。 | image | 与全话 contact sheet 并排人审；若确实跳变，回 comic-image 用同一风格锚和参考图重抽该格。 |
| warn | panel_style_outlier | 出图/第8话/panels/P019.png | 风格指纹内聚度 0.7472 明显低于本话中位 0.8076，疑似画风、细节密度或照片感跳变。 | image | 与全话 contact sheet 并排人审；若确实跳变，回 comic-image 用同一风格锚和参考图重抽该格。 |
| warn | panel_style_outlier | 出图/第8话/panels/P020.png | 风格指纹内聚度 0.7041 明显低于本话中位 0.8076，疑似画风、细节密度或照片感跳变。 | image | 与全话 contact sheet 并排人审；若确实跳变，回 comic-image 用同一风格锚和参考图重抽该格。 |
| warn | panel_style_outlier | 出图/第8话/panels/P022.png | 风格指纹内聚度 0.7573 明显低于本话中位 0.8076，疑似画风、细节密度或照片感跳变。 | image | 与全话 contact sheet 并排人审；若确实跳变，回 comic-image 用同一风格锚和参考图重抽该格。 |
| warn | panel_style_outlier | 出图/第8话/panels/P023.png | 风格指纹内聚度 0.7623 明显低于本话中位 0.8076，疑似画风、细节密度或照片感跳变。 | image | 与全话 contact sheet 并排人审；若确实跳变，回 comic-image 用同一风格锚和参考图重抽该格。 |
| warn | panel_style_outlier | 出图/第8话/panels/P024.png | 风格指纹内聚度 0.7563 明显低于本话中位 0.8076，疑似画风、细节密度或照片感跳变。 | image | 与全话 contact sheet 并排人审；若确实跳变，回 comic-image 用同一风格锚和参考图重抽该格。 |
| warn | panel_style_outlier | 出图/第8话/panels/P026.png | 风格指纹内聚度 0.7613 明显低于本话中位 0.8076，疑似画风、细节密度或照片感跳变。 | image | 与全话 contact sheet 并排人审；若确实跳变，回 comic-image 用同一风格锚和参考图重抽该格。 |
| warn | panel_style_outlier | 出图/第8话/panels/P043.png | 风格指纹内聚度 0.5683 明显低于本话中位 0.8076，疑似画风、细节密度或照片感跳变。 | image | 与全话 contact sheet 并排人审；若确实跳变，回 comic-image 用同一风格锚和参考图重抽该格。 |
| warn | panel_style_outlier | 出图/第8话/panels/P046.png | 风格指纹内聚度 0.7288 明显低于本话中位 0.8076，疑似画风、细节密度或照片感跳变。 | image | 与全话 contact sheet 并排人审；若确实跳变，回 comic-image 用同一风格锚和参考图重抽该格。 |
| warn | panel_style_outlier | 出图/第8话/panels/P048.png | 风格指纹内聚度 0.7604 明显低于本话中位 0.8076，疑似画风、细节密度或照片感跳变。 | image | 与全话 contact sheet 并排人审；若确实跳变，回 comic-image 用同一风格锚和参考图重抽该格。 |
| warn | tone_value_outlier | 出图/第8话/panels/P001.png | 黑白灰量化偏离话内中位：black_ratio=0.2805（中位 0.027），线宽代理 edge_density=0.0936（中位 0.137）。疑似网点密度/黑场/线宽口径不统一。 | image | 对照 finishing_plan 的 tone/black/ink 计划人审；口径确实漂了则统一收尾契约后重抽。 |
| warn | tone_value_outlier | 出图/第8话/panels/P004.png | 黑白灰量化偏离话内中位：black_ratio=0.2884（中位 0.027），线宽代理 edge_density=0.1055（中位 0.137）。疑似网点密度/黑场/线宽口径不统一。 | image | 对照 finishing_plan 的 tone/black/ink 计划人审；口径确实漂了则统一收尾契约后重抽。 |
| warn | tone_value_outlier | 出图/第8话/panels/P043.png | 黑白灰量化偏离话内中位：black_ratio=0.3583（中位 0.027），线宽代理 edge_density=0.0814（中位 0.137）。疑似网点密度/黑场/线宽口径不统一。 | image | 对照 finishing_plan 的 tone/black/ink 计划人审；口径确实漂了则统一收尾契约后重抽。 |
| warn | style_anchor_drift | 出图/共享/style_baseline.json | 本话整体指纹与风格锚图最高相似度仅 0.8656，风格锚可能已失去约束力。 | image | 并排比对锚图与本话 contact sheet；必要时更新风格锚或统一重抽。 |
| warn | hair_fingerprint_low | 出图/第8话/panels/P040.png | CHAR_CHEN_DA hair 指纹与参考图相似度偏低：score=0.297。这是色彩分布代理，需并排人审。 | image | 查看 character consistency contact sheet；如确实换脸/换发型/换服装，回 comic-image 用同一参考组重抽该格。 |
| warn | hair_fingerprint_low | 出图/第8话/panels/P042.png | CHAR_CHEN_DA hair 指纹与参考图相似度偏低：score=0.347。这是色彩分布代理，需并排人审。 | image | 查看 character consistency contact sheet；如确实换脸/换发型/换服装，回 comic-image 用同一参考组重抽该格。 |
| warn | hair_fingerprint_low | 出图/第8话/panels/P044.png | CHAR_CHEN_DA hair 指纹与参考图相似度偏低：score=0.312。这是色彩分布代理，需并排人审。 | image | 查看 character consistency contact sheet；如确实换脸/换发型/换服装，回 comic-image 用同一参考组重抽该格。 |
| warn | hair_fingerprint_low | 出图/第8话/panels/P048.png | CHAR_CHEN_DA hair 指纹与参考图相似度偏低：score=0.160。这是色彩分布代理，需并排人审。 | image | 查看 character consistency contact sheet；如确实换脸/换发型/换服装，回 comic-image 用同一参考组重抽该格。 |
| warn | face_fingerprint_low | 出图/第8话/panels/P027.png | CHAR_LI_JI face 指纹与参考图相似度偏低：score=0.429。这是色彩分布代理，需并排人审。 | image | 查看 character consistency contact sheet；如确实换脸/换发型/换服装，回 comic-image 用同一参考组重抽该格。 |
| warn | hair_fingerprint_low | 出图/第8话/panels/P027.png | CHAR_LI_JI hair 指纹与参考图相似度偏低：score=0.219。这是色彩分布代理，需并排人审。 | image | 查看 character consistency contact sheet；如确实换脸/换发型/换服装，回 comic-image 用同一参考组重抽该格。 |
| warn | hair_fingerprint_low | 出图/第8话/panels/P028.png | CHAR_LI_JI hair 指纹与参考图相似度偏低：score=0.399。这是色彩分布代理，需并排人审。 | image | 查看 character consistency contact sheet；如确实换脸/换发型/换服装，回 comic-image 用同一参考组重抽该格。 |
| warn | hair_fingerprint_low | 出图/第8话/panels/P001.png | CHAR_SHI_JIN hair 指纹与参考图相似度偏低：score=0.308。这是色彩分布代理，需并排人审。 | image | 查看 character consistency contact sheet；如确实换脸/换发型/换服装，回 comic-image 用同一参考组重抽该格。 |
| warn | hair_fingerprint_low | 出图/第8话/panels/P014.png | CHAR_SHI_JIN hair 指纹与参考图相似度偏低：score=0.452。这是色彩分布代理，需并排人审。 | image | 查看 character consistency contact sheet；如确实换脸/换发型/换服装，回 comic-image 用同一参考组重抽该格。 |
| warn | hair_fingerprint_low | 出图/第8话/panels/P040.png | CHAR_SHI_JIN hair 指纹与参考图相似度偏低：score=0.391。这是色彩分布代理，需并排人审。 | image | 查看 character consistency contact sheet；如确实换脸/换发型/换服装，回 comic-image 用同一参考组重抽该格。 |
| warn | hair_fingerprint_low | 出图/第8话/panels/P042.png | CHAR_SHI_JIN hair 指纹与参考图相似度偏低：score=0.411。这是色彩分布代理，需并排人审。 | image | 查看 character consistency contact sheet；如确实换脸/换发型/换服装，回 comic-image 用同一参考组重抽该格。 |
| warn | face_fingerprint_low | 出图/第8话/panels/P044.png | CHAR_SHI_JIN face 指纹与参考图相似度偏低：score=0.461。这是色彩分布代理，需并排人审。 | image | 查看 character consistency contact sheet；如确实换脸/换发型/换服装，回 comic-image 用同一参考组重抽该格。 |
| warn | hair_fingerprint_low | 出图/第8话/panels/P044.png | CHAR_SHI_JIN hair 指纹与参考图相似度偏低：score=0.388。这是色彩分布代理，需并排人审。 | image | 查看 character consistency contact sheet；如确实换脸/换发型/换服装，回 comic-image 用同一参考组重抽该格。 |
| warn | hair_fingerprint_low | 出图/第8话/panels/P048.png | CHAR_SHI_JIN hair 指纹与参考图相似度偏低：score=0.227。这是色彩分布代理，需并排人审。 | image | 查看 character consistency contact sheet；如确实换脸/换发型/换服装，回 comic-image 用同一参考组重抽该格。 |
| warn | hair_fingerprint_low | 出图/第8话/panels/P040.png | CHAR_YANG_CHUN hair 指纹与参考图相似度偏低：score=0.339。这是色彩分布代理，需并排人审。 | image | 查看 character consistency contact sheet；如确实换脸/换发型/换服装，回 comic-image 用同一参考组重抽该格。 |
| warn | hair_fingerprint_low | 出图/第8话/panels/P044.png | CHAR_YANG_CHUN hair 指纹与参考图相似度偏低：score=0.394。这是色彩分布代理，需并排人审。 | image | 查看 character consistency contact sheet；如确实换脸/换发型/换服装，回 comic-image 用同一参考组重抽该格。 |
| warn | face_fingerprint_low | 出图/第8话/panels/P048.png | CHAR_YANG_CHUN face 指纹与参考图相似度偏低：score=0.434。这是色彩分布代理，需并排人审。 | image | 查看 character consistency contact sheet；如确实换脸/换发型/换服装，回 comic-image 用同一参考组重抽该格。 |
| warn | hair_fingerprint_low | 出图/第8话/panels/P048.png | CHAR_YANG_CHUN hair 指纹与参考图相似度偏低：score=0.201。这是色彩分布代理，需并排人审。 | image | 查看 character consistency contact sheet；如确实换脸/换发型/换服装，回 comic-image 用同一参考组重抽该格。 |
| warn | face_fingerprint_low | 出图/第8话/panels/P040.png | CHAR_ZHU_WU face 指纹与参考图相似度偏低：score=0.486。这是色彩分布代理，需并排人审。 | image | 查看 character consistency contact sheet；如确实换脸/换发型/换服装，回 comic-image 用同一参考组重抽该格。 |
| warn | hair_fingerprint_low | 出图/第8话/panels/P040.png | CHAR_ZHU_WU hair 指纹与参考图相似度偏低：score=0.246。这是色彩分布代理，需并排人审。 | image | 查看 character consistency contact sheet；如确实换脸/换发型/换服装，回 comic-image 用同一参考组重抽该格。 |
| warn | hair_fingerprint_low | 出图/第8话/panels/P042.png | CHAR_ZHU_WU hair 指纹与参考图相似度偏低：score=0.290。这是色彩分布代理，需并排人审。 | image | 查看 character consistency contact sheet；如确实换脸/换发型/换服装，回 comic-image 用同一参考组重抽该格。 |
| warn | face_fingerprint_low | 出图/第8话/panels/P044.png | CHAR_ZHU_WU face 指纹与参考图相似度偏低：score=0.396。这是色彩分布代理，需并排人审。 | image | 查看 character consistency contact sheet；如确实换脸/换发型/换服装，回 comic-image 用同一参考组重抽该格。 |
| warn | hair_fingerprint_low | 出图/第8话/panels/P044.png | CHAR_ZHU_WU hair 指纹与参考图相似度偏低：score=0.252。这是色彩分布代理，需并排人审。 | image | 查看 character consistency contact sheet；如确实换脸/换发型/换服装，回 comic-image 用同一参考组重抽该格。 |
| warn | face_fingerprint_low | 出图/第8话/panels/P048.png | CHAR_ZHU_WU face 指纹与参考图相似度偏低：score=0.420。这是色彩分布代理，需并排人审。 | image | 查看 character consistency contact sheet；如确实换脸/换发型/换服装，回 comic-image 用同一参考组重抽该格。 |
| warn | hair_fingerprint_low | 出图/第8话/panels/P048.png | CHAR_ZHU_WU hair 指纹与参考图相似度偏低：score=0.129。这是色彩分布代理，需并排人审。 | image | 查看 character consistency contact sheet；如确实换脸/换发型/换服装，回 comic-image 用同一参考组重抽该格。 |
| warn | identity_similarity_engine_degraded | 生产数据/comic_character_consistency_第8话.json | CCIP 动漫身份 embedding 不可用，角色/生物相似度机检降级为色彩分布代理（同色调换脸/变形会漏报）。 | review | 独立 venv 安装 dghs-imgutils 后重跑 gate；在装好前必须以 VLM 并排裁决兜底身份轴。 |
| warn | vlm_judge_unadjudicated | 生产数据/comic_vlm_judge_tasks_第8话.json | VLM 并排判定任务包已生成 119 条但 0 条裁决——角色/生物身份、背景、道具三轴机检空转，画错生物形态这类漂移不会被拦。 | review | 由多模态 agent 逐条看图打分并写回 生产数据/comic_vlm_judge_verdicts_第8话.json 后重跑 gate。 |
| info | cross_chapter_drift | 生产数据/comic_identity_drift_report.json | CHAR_CHEN_DA 首崩 第8话：CHAR_CHEN_DA：仅 第8话 单话漂移——按该话 identity report 的 rerun_targets 重抽受影响格即可，先不升重资产。 | identity | 看 comic_identity_drift_report 决定补参考/补服装/补专门定妆或换后端。 |
| info | cross_chapter_drift | 生产数据/comic_identity_drift_report.json | CHAR_LI_JI 首崩 第7话：CHAR_LI_JI：跨 2 话反复漂移（第7话、第8话）——补专门定妆多视图（front/¾/side/back/face + 表情库），或换支持持久主体的后端（可灵/Seedream 主体库）按 ID 引用；漫画线不内置 LoRA，坚持一致性可本线外训练后把产出登记为 registry 参考。 | identity | 看 comic_identity_drift_report 决定补参考/补服装/补专门定妆或换后端。 |
| info | cross_chapter_drift | 生产数据/comic_identity_drift_report.json | CHAR_SHI_JIN 首崩 第5话：CHAR_SHI_JIN：跨 3 话反复漂移（第5话、第6话、第8话）——补专门定妆多视图（front/¾/side/back/face + 表情库），或换支持持久主体的后端（可灵/Seedream 主体库）按 ID 引用；漫画线不内置 LoRA，坚持一致性可本线外训练后把产出登记为 registry 参考。 | identity | 看 comic_identity_drift_report 决定补参考/补服装/补专门定妆或换后端。 |
| info | cross_chapter_drift | 生产数据/comic_identity_drift_report.json | CHAR_SHI_TAIGONG 首崩 第6话：CHAR_SHI_TAIGONG：第6话 服装漂移——在 registry.assets 的 outfits 子注册登记该换装（描述+参考图+绝不清单），重抽换装格；锁脸锁不住领型/纽扣/花纹。 | identity | 看 comic_identity_drift_report 决定补参考/补服装/补专门定妆或换后端。 |
| info | cross_chapter_drift | 生产数据/comic_identity_drift_report.json | CHAR_WANG_JIN 首崩 第4话：CHAR_WANG_JIN：第4话、第5话、第6话 服装漂移——在 registry.assets 的 outfits 子注册登记该换装（描述+参考图+绝不清单），重抽换装格；锁脸锁不住领型/纽扣/花纹。 | identity | 看 comic_identity_drift_report 决定补参考/补服装/补专门定妆或换后端。 |
| info | cross_chapter_drift | 生产数据/comic_identity_drift_report.json | CHAR_WANG_MOTHER 首崩 第5话：CHAR_WANG_MOTHER：第5话 服装漂移——在 registry.assets 的 outfits 子注册登记该换装（描述+参考图+绝不清单），重抽换装格；锁脸锁不住领型/纽扣/花纹。 | identity | 看 comic_identity_drift_report 决定补参考/补服装/补专门定妆或换后端。 |
| info | cross_chapter_drift | 生产数据/comic_identity_drift_report.json | CHAR_YANG_CHUN 首崩 第7话：CHAR_YANG_CHUN：跨 2 话反复漂移（第7话、第8话）——补专门定妆多视图（front/¾/side/back/face + 表情库），或换支持持久主体的后端（可灵/Seedream 主体库）按 ID 引用；漫画线不内置 LoRA，坚持一致性可本线外训练后把产出登记为 registry 参考。 | identity | 看 comic_identity_drift_report 决定补参考/补服装/补专门定妆或换后端。 |
| info | cross_chapter_drift | 生产数据/comic_identity_drift_report.json | CHAR_ZHU_WU 首崩 第8话：CHAR_ZHU_WU：仅 第8话 单话漂移——按该话 identity report 的 rerun_targets 重抽受影响格即可，先不升重资产。 | identity | 看 comic_identity_drift_report 决定补参考/补服装/补专门定妆或换后端。 |
| info | image | 出图/第8话/panels/P018.png | 疑似烘焙空白气泡已人审签收为误报：人工复核确认候选白区为山雾与天空自然留白，不是预烘焙气泡或文字容器；画面无文字，人物动作与场景可用。 | comic-review | 若该格重抽或构图变化，需要重新复核原始图空白气泡机检 |
| info | image | 出图/第8话/panels/P033.png | 疑似烘焙空白气泡已人审签收为误报：人工复核确认候选白区为晨昏天空自然留白，不是预烘焙气泡或文字容器；画面无文字，人物动作与场景可用。 | comic-review | 若该格重抽或构图变化，需要重新复核原始图空白气泡机检 |
| warn | style | 出图/第8话/panels/P001.png | 风格指纹内聚度 0.5622 明显低于本话中位 0.8076，疑似画风、细节密度或照片感跳变。 | comic-image | 与全话 contact sheet 并排人审；若确实跳变，回 comic-image 用同一风格锚和参考图重抽该格。 |
| warn | style | 出图/第8话/panels/P002.png | 风格指纹内聚度 0.7573 明显低于本话中位 0.8076，疑似画风、细节密度或照片感跳变。 | comic-image | 与全话 contact sheet 并排人审；若确实跳变，回 comic-image 用同一风格锚和参考图重抽该格。 |
| warn | style | 出图/第8话/panels/P004.png | 风格指纹内聚度 0.7321 明显低于本话中位 0.8076，疑似画风、细节密度或照片感跳变。 | comic-image | 与全话 contact sheet 并排人审；若确实跳变，回 comic-image 用同一风格锚和参考图重抽该格。 |
| warn | style | 出图/第8话/panels/P005.png | 风格指纹内聚度 0.7185 明显低于本话中位 0.8076，疑似画风、细节密度或照片感跳变。 | comic-image | 与全话 contact sheet 并排人审；若确实跳变，回 comic-image 用同一风格锚和参考图重抽该格。 |
| warn | style | 出图/第8话/panels/P007.png | 风格指纹内聚度 0.7342 明显低于本话中位 0.8076，疑似画风、细节密度或照片感跳变。 | comic-image | 与全话 contact sheet 并排人审；若确实跳变，回 comic-image 用同一风格锚和参考图重抽该格。 |
| warn | style | 出图/第8话/panels/P008.png | 风格指纹内聚度 0.6897 明显低于本话中位 0.8076，疑似画风、细节密度或照片感跳变。 | comic-image | 与全话 contact sheet 并排人审；若确实跳变，回 comic-image 用同一风格锚和参考图重抽该格。 |
| warn | style | 出图/第8话/panels/P018.png | 风格指纹内聚度 0.7386 明显低于本话中位 0.8076，疑似画风、细节密度或照片感跳变。 | comic-image | 与全话 contact sheet 并排人审；若确实跳变，回 comic-image 用同一风格锚和参考图重抽该格。 |
| warn | style | 出图/第8话/panels/P019.png | 风格指纹内聚度 0.7472 明显低于本话中位 0.8076，疑似画风、细节密度或照片感跳变。 | comic-image | 与全话 contact sheet 并排人审；若确实跳变，回 comic-image 用同一风格锚和参考图重抽该格。 |
| warn | style | 出图/第8话/panels/P020.png | 风格指纹内聚度 0.7041 明显低于本话中位 0.8076，疑似画风、细节密度或照片感跳变。 | comic-image | 与全话 contact sheet 并排人审；若确实跳变，回 comic-image 用同一风格锚和参考图重抽该格。 |
| warn | style | 出图/第8话/panels/P022.png | 风格指纹内聚度 0.7573 明显低于本话中位 0.8076，疑似画风、细节密度或照片感跳变。 | comic-image | 与全话 contact sheet 并排人审；若确实跳变，回 comic-image 用同一风格锚和参考图重抽该格。 |
| warn | style | 出图/第8话/panels/P023.png | 风格指纹内聚度 0.7623 明显低于本话中位 0.8076，疑似画风、细节密度或照片感跳变。 | comic-image | 与全话 contact sheet 并排人审；若确实跳变，回 comic-image 用同一风格锚和参考图重抽该格。 |
| warn | style | 出图/第8话/panels/P024.png | 风格指纹内聚度 0.7563 明显低于本话中位 0.8076，疑似画风、细节密度或照片感跳变。 | comic-image | 与全话 contact sheet 并排人审；若确实跳变，回 comic-image 用同一风格锚和参考图重抽该格。 |
| warn | style | 出图/第8话/panels/P026.png | 风格指纹内聚度 0.7613 明显低于本话中位 0.8076，疑似画风、细节密度或照片感跳变。 | comic-image | 与全话 contact sheet 并排人审；若确实跳变，回 comic-image 用同一风格锚和参考图重抽该格。 |
| warn | style | 出图/第8话/panels/P043.png | 风格指纹内聚度 0.5683 明显低于本话中位 0.8076，疑似画风、细节密度或照片感跳变。 | comic-image | 与全话 contact sheet 并排人审；若确实跳变，回 comic-image 用同一风格锚和参考图重抽该格。 |
| warn | style | 出图/第8话/panels/P046.png | 风格指纹内聚度 0.7288 明显低于本话中位 0.8076，疑似画风、细节密度或照片感跳变。 | comic-image | 与全话 contact sheet 并排人审；若确实跳变，回 comic-image 用同一风格锚和参考图重抽该格。 |
| warn | style | 出图/第8话/panels/P048.png | 风格指纹内聚度 0.7604 明显低于本话中位 0.8076，疑似画风、细节密度或照片感跳变。 | comic-image | 与全话 contact sheet 并排人审；若确实跳变，回 comic-image 用同一风格锚和参考图重抽该格。 |
| warn | style | 出图/第8话/panels/P001.png | 黑白灰量化偏离话内中位：black_ratio=0.2805（中位 0.027），线宽代理 edge_density=0.0936（中位 0.137）。疑似网点密度/黑场/线宽口径不统一。 | comic-image | 对照 finishing_plan 的 tone/black/ink 计划人审；口径确实漂了则统一收尾契约后重抽。 |
| warn | style | 出图/第8话/panels/P004.png | 黑白灰量化偏离话内中位：black_ratio=0.2884（中位 0.027），线宽代理 edge_density=0.1055（中位 0.137）。疑似网点密度/黑场/线宽口径不统一。 | comic-image | 对照 finishing_plan 的 tone/black/ink 计划人审；口径确实漂了则统一收尾契约后重抽。 |
| warn | style | 出图/第8话/panels/P043.png | 黑白灰量化偏离话内中位：black_ratio=0.3583（中位 0.027），线宽代理 edge_density=0.0814（中位 0.137）。疑似网点密度/黑场/线宽口径不统一。 | comic-image | 对照 finishing_plan 的 tone/black/ink 计划人审；口径确实漂了则统一收尾契约后重抽。 |
| warn | style | 出图/共享/style_baseline.json | 本话整体指纹与风格锚图最高相似度仅 0.8656，风格锚可能已失去约束力。 | comic-image | 并排比对锚图与本话 contact sheet；必要时更新风格锚或统一重抽。 |
| warn | character | 出图/第8话/panels/P040.png | CHAR_CHEN_DA hair 指纹与参考图相似度偏低：score=0.297。这是色彩分布代理，需并排人审。 | comic-image | 查看 character consistency contact sheet；如确实换脸/换发型/换服装，回 comic-image 用同一参考组重抽该格。 |
| warn | character | 出图/第8话/panels/P042.png | CHAR_CHEN_DA hair 指纹与参考图相似度偏低：score=0.347。这是色彩分布代理，需并排人审。 | comic-image | 查看 character consistency contact sheet；如确实换脸/换发型/换服装，回 comic-image 用同一参考组重抽该格。 |
| warn | character | 出图/第8话/panels/P044.png | CHAR_CHEN_DA hair 指纹与参考图相似度偏低：score=0.312。这是色彩分布代理，需并排人审。 | comic-image | 查看 character consistency contact sheet；如确实换脸/换发型/换服装，回 comic-image 用同一参考组重抽该格。 |
| warn | character | 出图/第8话/panels/P048.png | CHAR_CHEN_DA hair 指纹与参考图相似度偏低：score=0.160。这是色彩分布代理，需并排人审。 | comic-image | 查看 character consistency contact sheet；如确实换脸/换发型/换服装，回 comic-image 用同一参考组重抽该格。 |
| warn | character | 出图/第8话/panels/P027.png | CHAR_LI_JI face 指纹与参考图相似度偏低：score=0.429。这是色彩分布代理，需并排人审。 | comic-image | 查看 character consistency contact sheet；如确实换脸/换发型/换服装，回 comic-image 用同一参考组重抽该格。 |
| warn | character | 出图/第8话/panels/P027.png | CHAR_LI_JI hair 指纹与参考图相似度偏低：score=0.219。这是色彩分布代理，需并排人审。 | comic-image | 查看 character consistency contact sheet；如确实换脸/换发型/换服装，回 comic-image 用同一参考组重抽该格。 |
| warn | character | 出图/第8话/panels/P028.png | CHAR_LI_JI hair 指纹与参考图相似度偏低：score=0.399。这是色彩分布代理，需并排人审。 | comic-image | 查看 character consistency contact sheet；如确实换脸/换发型/换服装，回 comic-image 用同一参考组重抽该格。 |
| warn | character | 出图/第8话/panels/P001.png | CHAR_SHI_JIN hair 指纹与参考图相似度偏低：score=0.308。这是色彩分布代理，需并排人审。 | comic-image | 查看 character consistency contact sheet；如确实换脸/换发型/换服装，回 comic-image 用同一参考组重抽该格。 |
| warn | character | 出图/第8话/panels/P014.png | CHAR_SHI_JIN hair 指纹与参考图相似度偏低：score=0.452。这是色彩分布代理，需并排人审。 | comic-image | 查看 character consistency contact sheet；如确实换脸/换发型/换服装，回 comic-image 用同一参考组重抽该格。 |
| warn | character | 出图/第8话/panels/P040.png | CHAR_SHI_JIN hair 指纹与参考图相似度偏低：score=0.391。这是色彩分布代理，需并排人审。 | comic-image | 查看 character consistency contact sheet；如确实换脸/换发型/换服装，回 comic-image 用同一参考组重抽该格。 |
| warn | character | 出图/第8话/panels/P042.png | CHAR_SHI_JIN hair 指纹与参考图相似度偏低：score=0.411。这是色彩分布代理，需并排人审。 | comic-image | 查看 character consistency contact sheet；如确实换脸/换发型/换服装，回 comic-image 用同一参考组重抽该格。 |
| warn | character | 出图/第8话/panels/P044.png | CHAR_SHI_JIN face 指纹与参考图相似度偏低：score=0.461。这是色彩分布代理，需并排人审。 | comic-image | 查看 character consistency contact sheet；如确实换脸/换发型/换服装，回 comic-image 用同一参考组重抽该格。 |
| warn | character | 出图/第8话/panels/P044.png | CHAR_SHI_JIN hair 指纹与参考图相似度偏低：score=0.388。这是色彩分布代理，需并排人审。 | comic-image | 查看 character consistency contact sheet；如确实换脸/换发型/换服装，回 comic-image 用同一参考组重抽该格。 |
| warn | character | 出图/第8话/panels/P048.png | CHAR_SHI_JIN hair 指纹与参考图相似度偏低：score=0.227。这是色彩分布代理，需并排人审。 | comic-image | 查看 character consistency contact sheet；如确实换脸/换发型/换服装，回 comic-image 用同一参考组重抽该格。 |
| warn | character | 出图/第8话/panels/P040.png | CHAR_YANG_CHUN hair 指纹与参考图相似度偏低：score=0.339。这是色彩分布代理，需并排人审。 | comic-image | 查看 character consistency contact sheet；如确实换脸/换发型/换服装，回 comic-image 用同一参考组重抽该格。 |
| warn | character | 出图/第8话/panels/P044.png | CHAR_YANG_CHUN hair 指纹与参考图相似度偏低：score=0.394。这是色彩分布代理，需并排人审。 | comic-image | 查看 character consistency contact sheet；如确实换脸/换发型/换服装，回 comic-image 用同一参考组重抽该格。 |
| warn | character | 出图/第8话/panels/P048.png | CHAR_YANG_CHUN face 指纹与参考图相似度偏低：score=0.434。这是色彩分布代理，需并排人审。 | comic-image | 查看 character consistency contact sheet；如确实换脸/换发型/换服装，回 comic-image 用同一参考组重抽该格。 |
| warn | character | 出图/第8话/panels/P048.png | CHAR_YANG_CHUN hair 指纹与参考图相似度偏低：score=0.201。这是色彩分布代理，需并排人审。 | comic-image | 查看 character consistency contact sheet；如确实换脸/换发型/换服装，回 comic-image 用同一参考组重抽该格。 |
| warn | character | 出图/第8话/panels/P040.png | CHAR_ZHU_WU face 指纹与参考图相似度偏低：score=0.486。这是色彩分布代理，需并排人审。 | comic-image | 查看 character consistency contact sheet；如确实换脸/换发型/换服装，回 comic-image 用同一参考组重抽该格。 |
| warn | character | 出图/第8话/panels/P040.png | CHAR_ZHU_WU hair 指纹与参考图相似度偏低：score=0.246。这是色彩分布代理，需并排人审。 | comic-image | 查看 character consistency contact sheet；如确实换脸/换发型/换服装，回 comic-image 用同一参考组重抽该格。 |
| warn | character | 出图/第8话/panels/P042.png | CHAR_ZHU_WU hair 指纹与参考图相似度偏低：score=0.290。这是色彩分布代理，需并排人审。 | comic-image | 查看 character consistency contact sheet；如确实换脸/换发型/换服装，回 comic-image 用同一参考组重抽该格。 |
| warn | character | 出图/第8话/panels/P044.png | CHAR_ZHU_WU face 指纹与参考图相似度偏低：score=0.396。这是色彩分布代理，需并排人审。 | comic-image | 查看 character consistency contact sheet；如确实换脸/换发型/换服装，回 comic-image 用同一参考组重抽该格。 |
| warn | character | 出图/第8话/panels/P044.png | CHAR_ZHU_WU hair 指纹与参考图相似度偏低：score=0.252。这是色彩分布代理，需并排人审。 | comic-image | 查看 character consistency contact sheet；如确实换脸/换发型/换服装，回 comic-image 用同一参考组重抽该格。 |
| warn | character | 出图/第8话/panels/P048.png | CHAR_ZHU_WU face 指纹与参考图相似度偏低：score=0.420。这是色彩分布代理，需并排人审。 | comic-image | 查看 character consistency contact sheet；如确实换脸/换发型/换服装，回 comic-image 用同一参考组重抽该格。 |
| warn | character | 出图/第8话/panels/P048.png | CHAR_ZHU_WU hair 指纹与参考图相似度偏低：score=0.129。这是色彩分布代理，需并排人审。 | comic-image | 查看 character consistency contact sheet；如确实换脸/换发型/换服装，回 comic-image 用同一参考组重抽该格。 |
