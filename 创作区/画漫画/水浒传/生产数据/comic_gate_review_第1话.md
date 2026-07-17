# 漫画 Gate — review — 第1话

- 生成时间：2026-07-17T10:53:20
- 结论：warn
- block/warn/info：0 / 41 / 37

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
- comic-review report refreshed in review gate
- drift_report: 追踪 9 角色 · 有漂移 0（跨话汇总·advisory）

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
| info | panel_post_qc_warn | 出图/第1话/panels/P002.png | P002 的落盘 post_qc=warn 已人审签收为误报：接触表复核为紫宸殿地面受光与建筑留白，不是烘焙气泡或文字框。 | review | 若该格重抽或构图变化，需要重新复核 panel_qc。 |
| info | panel_post_qc_warn | 出图/第1话/panels/P015.png | P015 的落盘 post_qc=warn 已人审签收为误报：接触表复核为庭院天空、铺地与钟磬周边的自然负空间，不是烘焙气泡或文字框。 | review | 若该格重抽或构图变化，需要重新复核 panel_qc。 |
| info | panel_style_outlier | 出图/第1话/panels/P003.png | 风格指纹内聚度 0.7337 明显低于本话中位 0.8360，疑似画风、细节密度或照片感跳变。 | review | 已人审签收为计划内画面差异；若后续重抽该格需重新运行风格一致性机检。 |
| info | panel_style_outlier | 出图/第1话/panels/P007.png | 风格指纹内聚度 0.7942 明显低于本话中位 0.8360，疑似画风、细节密度或照片感跳变。 | review | 已人审签收为计划内画面差异；若后续重抽该格需重新运行风格一致性机检。 |
| info | panel_style_outlier | 出图/第1话/panels/P009.png | 风格指纹内聚度 0.6932 明显低于本话中位 0.8360，疑似画风、细节密度或照片感跳变。 | review | 已人审签收为计划内画面差异；若后续重抽该格需重新运行风格一致性机检。 |
| info | panel_style_outlier | 出图/第1话/panels/P011.png | 风格指纹内聚度 0.7872 明显低于本话中位 0.8360，疑似画风、细节密度或照片感跳变。 | review | 已人审签收为计划内画面差异；若后续重抽该格需重新运行风格一致性机检。 |
| info | panel_style_outlier | 出图/第1话/panels/P014.png | 风格指纹内聚度 0.7606 明显低于本话中位 0.8360，疑似画风、细节密度或照片感跳变。 | review | 已人审签收为计划内画面差异；若后续重抽该格需重新运行风格一致性机检。 |
| info | panel_style_outlier | 出图/第1话/panels/P018.png | 风格指纹内聚度 0.6841 明显低于本话中位 0.8360，疑似画风、细节密度或照片感跳变。 | review | 已人审签收为计划内画面差异；若后续重抽该格需重新运行风格一致性机检。 |
| info | panel_style_outlier | 出图/第1话/panels/P021.png | 风格指纹内聚度 0.7690 明显低于本话中位 0.8360，疑似画风、细节密度或照片感跳变。 | review | 已人审签收为计划内画面差异；若后续重抽该格需重新运行风格一致性机检。 |
| info | panel_style_outlier | 出图/第1话/panels/P034.png | 风格指纹内聚度 0.7472 明显低于本话中位 0.8360，疑似画风、细节密度或照片感跳变。 | review | 已人审签收为计划内画面差异；若后续重抽该格需重新运行风格一致性机检。 |
| info | panel_style_outlier | 出图/第1话/panels/P046.png | 风格指纹内聚度 0.7125 明显低于本话中位 0.8360，疑似画风、细节密度或照片感跳变。 | review | 已人审签收为计划内画面差异；若后续重抽该格需重新运行风格一致性机检。 |
| info | panel_style_outlier | 出图/第1话/panels/P047.png | 风格指纹内聚度 0.7204 明显低于本话中位 0.8360，疑似画风、细节密度或照片感跳变。 | review | 已人审签收为计划内画面差异；若后续重抽该格需重新运行风格一致性机检。 |
| info | location_color_grade_shift | 出图/第1话/panels/P018.png | 同场景“上清宫方丈”内调色代理偏离组中位：warmth_dev=0.244, tint_dev=0.031。 | review | 已人审签收为计划内画面差异；若后续重抽该格需重新运行风格一致性机检。 |
| info | tone_value_outlier | 出图/第1话/panels/P046.png | 黑白灰量化偏离话内中位：black_ratio=0.2547（中位 0.009），线宽代理 edge_density=0.0792（中位 0.122）。疑似网点密度/黑场/线宽口径不统一。 | review | 已人审签收为计划内画面差异；若后续重抽该格需重新运行风格一致性机检。 |
| info | face_fingerprint_low | 出图/第1话/panels/P004.png | CHAR_WEN_YANBO face 指纹与参考图相似度偏低：score=0.451。这是色彩分布代理，需并排人审。 | review | 已人审签收为计划内角色状态差异；若后续重抽该格需重新运行角色一致性机检。 |
| info | hair_fingerprint_low | 出图/第1话/panels/P004.png | CHAR_WEN_YANBO hair 指纹与参考图相似度偏低：score=0.168。这是色彩分布代理，需并排人审。 | review | 已人审签收为计划内角色状态差异；若后续重抽该格需重新运行角色一致性机检。 |
| info | outfit_fingerprint_low | 出图/第1话/panels/P004.png | CHAR_WEN_YANBO outfit 指纹与参考图相似度偏低：score=0.329。这是色彩分布代理，需并排人审。 | review | 已人审签收为计划内角色状态差异；若后续重抽该格需重新运行角色一致性机检。 |
| info | hair_fingerprint_low | 出图/第1话/panels/P005.png | CHAR_WEN_YANBO hair 指纹与参考图相似度偏低：score=0.296。这是色彩分布代理，需并排人审。 | review | 已人审签收为计划内角色状态差异；若后续重抽该格需重新运行角色一致性机检。 |
| warn | prop_reference_missing | 出图/共享/identity_registry.json | OUTFIT_BASE 在本话出场（P003,P004,P005,P006,P008,P009,P010,P012）但没有参考图，无法并排核对同一物。 | image | 用 comic-identity anchors 生成/登记该道具锚点图后重建出图包。 |
| warn | prop_reference_missing | 出图/共享/identity_registry.json | OUTFIT_COURT_ENVOY 在本话出场（P010,P011,P012,P016,P017,P018,P042,P043）但没有参考图，无法并排核对同一物。 | image | 用 comic-identity anchors 生成/登记该道具锚点图后重建出图包。 |
| warn | prop_reference_missing | 出图/共享/identity_registry.json | OUTFIT_HERDBOY 在本话出场（P034,P035,P036,P037,P038）但没有参考图，无法并排核对同一物。 | image | 用 comic-identity anchors 生成/登记该道具锚点图后重建出图包。 |
| warn | prop_reference_missing | 出图/共享/identity_registry.json | OUTFIT_MOUNTAIN_PLAIN 在本话出场（P019,P020,P021,P022,P023,P024,P025,P026）但没有参考图，无法并排核对同一物。 | image | 用 comic-identity anchors 生成/登记该道具锚点图后重建出图包。 |
| warn | prop_reference_missing | 出图/共享/identity_registry.json | VFX_108_STARLIGHTS 在本话出场（P047,P048）但没有参考图，无法并排核对同一物。 | image | 用 comic-identity anchors 生成/登记该道具锚点图后重建出图包。 |
| info | image | 出图/第1话/panels/P002.png | 疑似烘焙空白气泡已人审签收为误报：接触表复核为紫宸殿地面受光与建筑留白，不是烘焙气泡或文字框。 | comic-review | 若该格重抽或构图变化，需要重新复核原始图空白气泡机检 |
| info | image | 出图/第1话/panels/P015.png | 疑似烘焙空白气泡已人审签收为误报：接触表复核为庭院天空、铺地与钟磬周边的自然负空间，不是烘焙气泡或文字框。 | comic-review | 若该格重抽或构图变化，需要重新复核原始图空白气泡机检 |
| info | style | 出图/第1话/panels/P003.png | 风格指纹内聚度 0.7337 明显低于本话中位 0.8360，疑似画风、细节密度或照片感跳变。 | comic-review | 已人审签收为计划内画面差异；若后续重抽该格需重新运行风格一致性机检。 |
| info | style | 出图/第1话/panels/P007.png | 风格指纹内聚度 0.7942 明显低于本话中位 0.8360，疑似画风、细节密度或照片感跳变。 | comic-review | 已人审签收为计划内画面差异；若后续重抽该格需重新运行风格一致性机检。 |
| info | style | 出图/第1话/panels/P009.png | 风格指纹内聚度 0.6932 明显低于本话中位 0.8360，疑似画风、细节密度或照片感跳变。 | comic-review | 已人审签收为计划内画面差异；若后续重抽该格需重新运行风格一致性机检。 |
| info | style | 出图/第1话/panels/P011.png | 风格指纹内聚度 0.7872 明显低于本话中位 0.8360，疑似画风、细节密度或照片感跳变。 | comic-review | 已人审签收为计划内画面差异；若后续重抽该格需重新运行风格一致性机检。 |
| info | style | 出图/第1话/panels/P014.png | 风格指纹内聚度 0.7606 明显低于本话中位 0.8360，疑似画风、细节密度或照片感跳变。 | comic-review | 已人审签收为计划内画面差异；若后续重抽该格需重新运行风格一致性机检。 |
| info | style | 出图/第1话/panels/P018.png | 风格指纹内聚度 0.6841 明显低于本话中位 0.8360，疑似画风、细节密度或照片感跳变。 | comic-review | 已人审签收为计划内画面差异；若后续重抽该格需重新运行风格一致性机检。 |
| info | style | 出图/第1话/panels/P021.png | 风格指纹内聚度 0.7690 明显低于本话中位 0.8360，疑似画风、细节密度或照片感跳变。 | comic-review | 已人审签收为计划内画面差异；若后续重抽该格需重新运行风格一致性机检。 |
| info | style | 出图/第1话/panels/P034.png | 风格指纹内聚度 0.7472 明显低于本话中位 0.8360，疑似画风、细节密度或照片感跳变。 | comic-review | 已人审签收为计划内画面差异；若后续重抽该格需重新运行风格一致性机检。 |
| info | style | 出图/第1话/panels/P046.png | 风格指纹内聚度 0.7125 明显低于本话中位 0.8360，疑似画风、细节密度或照片感跳变。 | comic-review | 已人审签收为计划内画面差异；若后续重抽该格需重新运行风格一致性机检。 |
| info | style | 出图/第1话/panels/P047.png | 风格指纹内聚度 0.7204 明显低于本话中位 0.8360，疑似画风、细节密度或照片感跳变。 | comic-review | 已人审签收为计划内画面差异；若后续重抽该格需重新运行风格一致性机检。 |
| info | style | 出图/第1话/panels/P018.png | 同场景“上清宫方丈”内调色代理偏离组中位：warmth_dev=0.244, tint_dev=0.031。 | comic-review | 已人审签收为计划内画面差异；若后续重抽该格需重新运行风格一致性机检。 |
| info | style | 出图/第1话/panels/P046.png | 黑白灰量化偏离话内中位：black_ratio=0.2547（中位 0.009），线宽代理 edge_density=0.0792（中位 0.122）。疑似网点密度/黑场/线宽口径不统一。 | comic-review | 已人审签收为计划内画面差异；若后续重抽该格需重新运行风格一致性机检。 |
| info | character | 出图/第1话/panels/P004.png | CHAR_WEN_YANBO face 指纹与参考图相似度偏低：score=0.451。这是色彩分布代理，需并排人审。 | comic-review | 已人审签收为计划内角色状态差异；若后续重抽该格需重新运行角色一致性机检。 |
| info | character | 出图/第1话/panels/P004.png | CHAR_WEN_YANBO hair 指纹与参考图相似度偏低：score=0.168。这是色彩分布代理，需并排人审。 | comic-review | 已人审签收为计划内角色状态差异；若后续重抽该格需重新运行角色一致性机检。 |
| info | character | 出图/第1话/panels/P004.png | CHAR_WEN_YANBO outfit 指纹与参考图相似度偏低：score=0.329。这是色彩分布代理，需并排人审。 | comic-review | 已人审签收为计划内角色状态差异；若后续重抽该格需重新运行角色一致性机检。 |
| info | character | 出图/第1话/panels/P005.png | CHAR_WEN_YANBO hair 指纹与参考图相似度偏低：score=0.296。这是色彩分布代理，需并排人审。 | comic-review | 已人审签收为计划内角色状态差异；若后续重抽该格需重新运行角色一致性机检。 |
