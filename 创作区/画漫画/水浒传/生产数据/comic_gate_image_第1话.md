# 漫画 Gate — image — 第1话

- 生成时间：2026-07-16T20:35:53
- 结论：warn
- block/warn/info：0 / 57 / 1

## 记录

- 开发包严格合同: pass
- 源范围/SHA/逐格 coverage 合同: pass
- continuity_audit: chapters=1 block=0 warn=0
- 缩略分镜/name board 审批合同: pass
- 排版审批合同: pass
- 原稿收尾合同: pass
- backend adapter: dreamina_image2image; reference_image_limit=10; persistent_subject=False
- 角色注册表 v2: pass
- 角色多视图技术齐套与人审签收: pass
- chapter_beat_audit: must=0 warn=0（advisory·不阻断）
- setup_payoff_ledger: must=0 warn=0（advisory·不阻断）
- reentry_context_audit: must=0 warn=0（advisory·不阻断）
- redundancy_audit: must=0 warn=0（advisory·不阻断）
- subtext_audit: must=0 warn=0（advisory·不阻断）
- reference_planner: 含角色格 42 需处理 35；处方 SHA 已校验
- panel_variety: panels=48 近重复对=0（advisory·不阻断）
- style consistency refreshed: 生产数据/comic_style_consistency_第1话.md
- character consistency refreshed: 生产数据/comic_character_consistency_第1话.md
- scene/prop consistency refreshed: 生产数据/comic_scene_prop_consistency_第1话.md

## Findings

| severity | code | artifact | reason | return_to | suggested_fix |
|---|---|---|---|---|---|
| warn | compiled_prompt_advisory | 出图/第1话/prompt/panel_jobs.json | P046: submit_prompt_verbose:1481 | image | 精简本格可见画面描述后重建 panel_jobs。 |
| warn | compiled_prompt_advisory | 出图/第1话/prompt/panel_jobs.json | P047: submit_prompt_verbose:1584 | image | 精简本格可见画面描述后重建 panel_jobs。 |
| warn | compiled_prompt_advisory | 出图/第1话/prompt/panel_jobs.json | P048: submit_prompt_verbose:1521 | image | 精简本格可见画面描述后重建 panel_jobs。 |
| info | climax_at_tail | 生产数据/comic_chapter_beat_audit_第1话.json | 高潮候选在 98%；确认中段是否有足够支撑。 | comic-script | 按机检建议回 comic-script 修分话/分格后重跑。 |
| warn | missing_reference | 生产数据/comic_reference_plan_第1话.json | P006·宋仁宗：缺 45°/three_quarter 参考（档位或本格变化量需要） | identity | 按处方补该角色缺的视图/表情/服装参考并重建出图包。 |
| warn | missing_reference | 生产数据/comic_reference_plan_第1话.json | P006·宋仁宗：缺 45°/¾ 侧脸参考（动作格主身份锚·避免 frontal 摆拍偏置） | identity | 按处方补该角色缺的视图/表情/服装参考并重建出图包。 |
| warn | same_frame_color_collision | 生产数据/comic_reference_plan_第1话.json | P008 多人同框主色撞色（易串脸）：CHAR_FAN_ZHONGYAN↔CHAR_EMPEROR_RENZONG（同主色「红」）——用互斥发色/服装主色/配饰强分，必要时拆反打。 | identity | 按处方补该角色缺的视图/表情/服装参考并重建出图包。 |
| warn | missing_reference | 生产数据/comic_reference_plan_第1话.json | P010·宋仁宗：缺 45°/three_quarter 参考（档位或本格变化量需要） | identity | 按处方补该角色缺的视图/表情/服装参考并重建出图包。 |
| warn | strong_emotion_expression_reference_missing | 生产数据/comic_reference_plan_第1话.json | P010·宋仁宗：缺 强情绪格缺对应表情参考（expression_id=EXPR_NEUTRAL；不能用中性 face 冒充） | identity | 按处方补该角色缺的视图/表情/服装参考并重建出图包。 |
| warn | strong_emotion_expression_reference_missing | 生产数据/comic_reference_plan_第1话.json | P010·洪信：缺 强情绪格缺对应表情参考（expression_id=EXPR_COMPOSED；不能用中性 face 冒充） | identity | 按处方补该角色缺的视图/表情/服装参考并重建出图包。 |
| warn | missing_reference | 生产数据/comic_reference_plan_第1话.json | P020·洪信：缺 侧脸参考（极端角度/转头/过肩格） | identity | 按处方补该角色缺的视图/表情/服装参考并重建出图包。 |
| warn | missing_reference | 生产数据/comic_reference_plan_第1话.json | P020·洪信：缺 背身参考（背影/过肩格） | identity | 按处方补该角色缺的视图/表情/服装参考并重建出图包。 |
| warn | missing_reference | 生产数据/comic_reference_plan_第1话.json | P020·上清宫住持：缺 侧脸参考（极端角度/转头/过肩格） | identity | 按处方补该角色缺的视图/表情/服装参考并重建出图包。 |
| warn | missing_reference | 生产数据/comic_reference_plan_第1话.json | P020·上清宫住持：缺 背身参考（背影/过肩格） | identity | 按处方补该角色缺的视图/表情/服装参考并重建出图包。 |
| warn | strong_emotion_expression_reference_missing | 生产数据/comic_reference_plan_第1话.json | P023·洪信：缺 强情绪格缺对应表情参考（expression_id=EXPR_COMPOSED；不能用中性 face 冒充） | identity | 按处方补该角色缺的视图/表情/服装参考并重建出图包。 |
| warn | missing_reference | 生产数据/comic_reference_plan_第1话.json | P025·洪信：缺 侧脸参考（极端角度/转头/过肩格） | identity | 按处方补该角色缺的视图/表情/服装参考并重建出图包。 |
| warn | missing_reference | 生产数据/comic_reference_plan_第1话.json | P025·吊睛白额锦毛大虫：缺 侧脸参考（极端角度/转头/过肩格） | identity | 按处方补该角色缺的视图/表情/服装参考并重建出图包。 |
| warn | strong_emotion_expression_reference_missing | 生产数据/comic_reference_plan_第1话.json | P026·洪信：缺 强情绪格缺对应表情参考（expression_id=EXPR_TERRIFIED；不能用中性 face 冒充） | identity | 按处方补该角色缺的视图/表情/服装参考并重建出图包。 |
| warn | strong_emotion_expression_reference_missing | 生产数据/comic_reference_plan_第1话.json | P026·吊睛白额锦毛大虫：缺 强情绪格缺对应表情参考（expression_id=EXPR_NEUTRAL；不能用中性 face 冒充） | identity | 按处方补该角色缺的视图/表情/服装参考并重建出图包。 |
| warn | strong_emotion_expression_reference_missing | 生产数据/comic_reference_plan_第1话.json | P028·洪信：缺 强情绪格缺对应表情参考（expression_id=EXPR_TERRIFIED；不能用中性 face 冒充） | identity | 按处方补该角色缺的视图/表情/服装参考并重建出图包。 |
| warn | multi_character_closeup | 生产数据/comic_reference_plan_第1话.json | P030 多人近景=串脸最高发档：优先拆单人CU+反打或降景别，坚持同框须登记分区/分别出图+合成。 | identity | 按处方补该角色缺的视图/表情/服装参考并重建出图包。 |
| warn | strong_emotion_expression_reference_missing | 生产数据/comic_reference_plan_第1话.json | P033·洪信：缺 强情绪格缺对应表情参考（expression_id=EXPR_TERRIFIED；不能用中性 face 冒充） | identity | 按处方补该角色缺的视图/表情/服装参考并重建出图包。 |
| warn | strong_emotion_expression_reference_missing | 生产数据/comic_reference_plan_第1话.json | P033·雪花大蛇：缺 强情绪格缺对应表情参考（expression_id=EXPR_NEUTRAL；不能用中性 face 冒充） | identity | 按处方补该角色缺的视图/表情/服装参考并重建出图包。 |
| warn | strong_emotion_expression_reference_missing | 生产数据/comic_reference_plan_第1话.json | P038·洪信：缺 强情绪格缺对应表情参考（expression_id=EXPR_TERRIFIED；不能用中性 face 冒充） | identity | 按处方补该角色缺的视图/表情/服装参考并重建出图包。 |
| warn | strong_emotion_expression_reference_missing | 生产数据/comic_reference_plan_第1话.json | P038·虚靖天师：缺 强情绪格缺对应表情参考（expression_id=EXPR_KNOWING_SMILE；不能用中性 face 冒充） | identity | 按处方补该角色缺的视图/表情/服装参考并重建出图包。 |
| warn | strong_emotion_expression_reference_missing | 生产数据/comic_reference_plan_第1话.json | P039·洪信：缺 强情绪格缺对应表情参考（expression_id=EXPR_TERRIFIED；不能用中性 face 冒充） | identity | 按处方补该角色缺的视图/表情/服装参考并重建出图包。 |
| warn | strong_emotion_expression_reference_missing | 生产数据/comic_reference_plan_第1话.json | P039·上清宫住持：缺 强情绪格缺对应表情参考（expression_id=EXPR_NEUTRAL；不能用中性 face 冒充） | identity | 按处方补该角色缺的视图/表情/服装参考并重建出图包。 |
| warn | strong_emotion_expression_reference_missing | 生产数据/comic_reference_plan_第1话.json | P040·洪信：缺 强情绪格缺对应表情参考（expression_id=EXPR_TERRIFIED；不能用中性 face 冒充） | identity | 按处方补该角色缺的视图/表情/服装参考并重建出图包。 |
| warn | strong_emotion_expression_reference_missing | 生产数据/comic_reference_plan_第1话.json | P040·上清宫住持：缺 强情绪格缺对应表情参考（expression_id=EXPR_NEUTRAL；不能用中性 face 冒充） | identity | 按处方补该角色缺的视图/表情/服装参考并重建出图包。 |
| warn | multi_character_closeup | 生产数据/comic_reference_plan_第1话.json | P042 多人近景=串脸最高发档：优先拆单人CU+反打或降景别，坚持同框须登记分区/分别出图+合成。 | identity | 按处方补该角色缺的视图/表情/服装参考并重建出图包。 |
| warn | strong_emotion_expression_reference_missing | 生产数据/comic_reference_plan_第1话.json | P044·洪信：缺 强情绪格缺对应表情参考（expression_id=EXPR_DEFIANT；不能用中性 face 冒充） | identity | 按处方补该角色缺的视图/表情/服装参考并重建出图包。 |
| warn | strong_emotion_expression_reference_missing | 生产数据/comic_reference_plan_第1话.json | P044·上清宫住持：缺 强情绪格缺对应表情参考（expression_id=EXPR_NEUTRAL；不能用中性 face 冒充） | identity | 按处方补该角色缺的视图/表情/服装参考并重建出图包。 |
| warn | multi_character_closeup | 生产数据/comic_reference_plan_第1话.json | P047 多人近景=串脸最高发档：优先拆单人CU+反打或降景别，坚持同框须登记分区/分别出图+合成。 | identity | 按处方补该角色缺的视图/表情/服装参考并重建出图包。 |
| warn | strong_emotion_expression_reference_missing | 生产数据/comic_reference_plan_第1话.json | P048·洪信：缺 强情绪格缺对应表情参考（expression_id=EXPR_STUNNED；不能用中性 face 冒充） | identity | 按处方补该角色缺的视图/表情/服装参考并重建出图包。 |
| warn | missing_reference | 生产数据/comic_reference_plan_第1话.json | P048·洪信：缺 全身/三视图参考（远景/全身动作格·单张头肩定妆不够） | identity | 按处方补该角色缺的视图/表情/服装参考并重建出图包。 |
| warn | strong_emotion_expression_reference_missing | 生产数据/comic_reference_plan_第1话.json | P048·上清宫住持：缺 强情绪格缺对应表情参考（expression_id=EXPR_NEUTRAL；不能用中性 face 冒充） | identity | 按处方补该角色缺的视图/表情/服装参考并重建出图包。 |
| warn | missing_reference | 生产数据/comic_reference_plan_第1话.json | P048·上清宫住持：缺 全身/三视图参考（远景/全身动作格·单张头肩定妆不够） | identity | 按处方补该角色缺的视图/表情/服装参考并重建出图包。 |
| warn | panel_post_qc_warn | 出图/第1话/panels/P002.png | P002 的落盘 post_qc=warn，需要人审签收或重抽。 | image | 放大查看 panel_qc 与原图；确认误报时在审查报告保留签收证据。 |
| warn | panel_post_qc_warn | 出图/第1话/panels/P006.png | P006 的落盘 post_qc=warn，需要人审签收或重抽。 | image | 放大查看 panel_qc 与原图；确认误报时在审查报告保留签收证据。 |
| warn | panel_style_outlier | 出图/第1话/panels/P003.png | 风格指纹内聚度 0.7279 明显低于本话中位 0.8376，疑似画风、细节密度或照片感跳变。 | image | 与全话 contact sheet 并排人审；若确实跳变，回 comic-image 用同一风格锚和参考图重抽该格。 |
| warn | panel_style_outlier | 出图/第1话/panels/P007.png | 风格指纹内聚度 0.7831 明显低于本话中位 0.8376，疑似画风、细节密度或照片感跳变。 | image | 与全话 contact sheet 并排人审；若确实跳变，回 comic-image 用同一风格锚和参考图重抽该格。 |
| warn | panel_style_outlier | 出图/第1话/panels/P012.png | 风格指纹内聚度 0.7964 明显低于本话中位 0.8376，疑似画风、细节密度或照片感跳变。 | image | 与全话 contact sheet 并排人审；若确实跳变，回 comic-image 用同一风格锚和参考图重抽该格。 |
| warn | panel_style_outlier | 出图/第1话/panels/P018.png | 风格指纹内聚度 0.6771 明显低于本话中位 0.8376，疑似画风、细节密度或照片感跳变。 | image | 与全话 contact sheet 并排人审；若确实跳变，回 comic-image 用同一风格锚和参考图重抽该格。 |
| warn | panel_style_outlier | 出图/第1话/panels/P021.png | 风格指纹内聚度 0.7621 明显低于本话中位 0.8376，疑似画风、细节密度或照片感跳变。 | image | 与全话 contact sheet 并排人审；若确实跳变，回 comic-image 用同一风格锚和参考图重抽该格。 |
| warn | panel_style_outlier | 出图/第1话/panels/P030.png | 风格指纹内聚度 0.7958 明显低于本话中位 0.8376，疑似画风、细节密度或照片感跳变。 | image | 与全话 contact sheet 并排人审；若确实跳变，回 comic-image 用同一风格锚和参考图重抽该格。 |
| warn | panel_style_outlier | 出图/第1话/panels/P046.png | 风格指纹内聚度 0.7080 明显低于本话中位 0.8376，疑似画风、细节密度或照片感跳变。 | image | 与全话 contact sheet 并排人审；若确实跳变，回 comic-image 用同一风格锚和参考图重抽该格。 |
| warn | panel_style_outlier | 出图/第1话/panels/P047.png | 风格指纹内聚度 0.7141 明显低于本话中位 0.8376，疑似画风、细节密度或照片感跳变。 | image | 与全话 contact sheet 并排人审；若确实跳变，回 comic-image 用同一风格锚和参考图重抽该格。 |
| warn | location_color_grade_shift | 出图/第1话/panels/P018.png | 同场景“上清宫方丈”内调色代理偏离组中位：warmth_dev=0.244, tint_dev=0.031。 | image | 人审确认是否为有意光效；否则统一白平衡/冷暖光口径后重抽该格。 |
| warn | tone_value_outlier | 出图/第1话/panels/P046.png | 黑白灰量化偏离话内中位：black_ratio=0.2547（中位 0.008），线宽代理 edge_density=0.0792（中位 0.123）。疑似网点密度/黑场/线宽口径不统一。 | image | 对照 finishing_plan 的 tone/black/ink 计划人审；口径确实漂了则统一收尾契约后重抽。 |
| warn | face_fingerprint_low | 出图/第1话/panels/P004.png | CHAR_WEN_YANBO face 指纹与参考图相似度偏低：score=0.451。这是色彩分布代理，需并排人审。 | image | 查看 character consistency contact sheet；如确实换脸/换发型/换服装，回 comic-image 用同一参考组重抽该格。 |
| warn | hair_fingerprint_low | 出图/第1话/panels/P004.png | CHAR_WEN_YANBO hair 指纹与参考图相似度偏低：score=0.168。这是色彩分布代理，需并排人审。 | image | 查看 character consistency contact sheet；如确实换脸/换发型/换服装，回 comic-image 用同一参考组重抽该格。 |
| warn | outfit_fingerprint_low | 出图/第1话/panels/P004.png | CHAR_WEN_YANBO outfit 指纹与参考图相似度偏低：score=0.329。这是色彩分布代理，需并排人审。 | image | 查看 character consistency contact sheet；如确实换脸/换发型/换服装，回 comic-image 用同一参考组重抽该格。 |
| warn | hair_fingerprint_low | 出图/第1话/panels/P005.png | CHAR_WEN_YANBO hair 指纹与参考图相似度偏低：score=0.296。这是色彩分布代理，需并排人审。 | image | 查看 character consistency contact sheet；如确实换脸/换发型/换服装，回 comic-image 用同一参考组重抽该格。 |
| warn | prop_reference_missing | 出图/共享/identity_registry.json | OUTFIT_BASE 在本话出场（P003,P004,P005,P006,P008,P009,P010,P012）但没有参考图，无法并排核对同一物。 | image | 用 comic-identity anchors 生成/登记该道具锚点图后重建出图包。 |
| warn | prop_reference_missing | 出图/共享/identity_registry.json | OUTFIT_COURT_ENVOY 在本话出场（P010,P011,P012,P016,P017,P018,P042,P043）但没有参考图，无法并排核对同一物。 | image | 用 comic-identity anchors 生成/登记该道具锚点图后重建出图包。 |
| warn | prop_reference_missing | 出图/共享/identity_registry.json | OUTFIT_HERDBOY 在本话出场（P034,P035,P036,P037,P038）但没有参考图，无法并排核对同一物。 | image | 用 comic-identity anchors 生成/登记该道具锚点图后重建出图包。 |
| warn | prop_reference_missing | 出图/共享/identity_registry.json | OUTFIT_MOUNTAIN_PLAIN 在本话出场（P019,P020,P021,P022,P023,P024,P025,P026）但没有参考图，无法并排核对同一物。 | image | 用 comic-identity anchors 生成/登记该道具锚点图后重建出图包。 |
| warn | prop_reference_missing | 出图/共享/identity_registry.json | VFX_108_STARLIGHTS 在本话出场（P047,P048）但没有参考图，无法并排核对同一物。 | image | 用 comic-identity anchors 生成/登记该道具锚点图后重建出图包。 |
