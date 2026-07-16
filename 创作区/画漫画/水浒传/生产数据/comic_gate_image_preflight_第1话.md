# 漫画 Gate — image_preflight — 第1话

- 生成时间：2026-07-16T20:51:01
- 结论：warn
- block/warn/info：0 / 36 / 1

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
