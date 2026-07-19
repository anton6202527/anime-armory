# 漫画 Gate — compose — 第4话

- 生成时间：2026-07-19T13:40:50
- 结论：warn
- block/warn/info：0 / 44 / 1

## 记录

- 开发包严格合同: pass
- 源范围/SHA/逐格 coverage 合同: pass
- continuity_audit: chapters=4 block=0 warn=0
- 缩略分镜/name board 审批合同: pass
- 排版审批合同: pass
- 原稿收尾合同: pass
- backend adapter: dreamina_image2image; reference_image_limit=10; persistent_subject=False
- 角色注册表 v2: pass
- 角色多视图技术齐套与人审签收: pass
- chapter_beat_audit: must=0 warn=0（advisory·不阻断）
- setup_payoff_ledger: must=0 warn=0（advisory·不阻断）
- reentry_context_audit: must=0 warn=0（advisory·不阻断）
- entity_presence_audit: must=0 warn=0（advisory·不阻断）
- redundancy_audit: must=0 warn=0（advisory·不阻断）
- subtext_audit: must=0 warn=0（advisory·不阻断）
- reference_planner: 含角色格 43 需处理 27；处方 SHA 已校验
- panel_variety: panels=46 近重复对=0（advisory·不阻断）
- style consistency refreshed: 生产数据/comic_style_consistency_第4话.md
- character consistency refreshed: 生产数据/comic_character_consistency_第4话.md
- scene/prop consistency refreshed: 生产数据/comic_scene_prop_consistency_第4话.md

## Findings

| severity | code | artifact | reason | return_to | suggested_fix |
|---|---|---|---|---|---|
| info | climax_at_tail | 生产数据/comic_chapter_beat_audit_第4话.json | 高潮候选在 91%；确认中段是否有足够支撑。 | comic-script | 按机检建议回 comic-script 修分话/分格后重跑。 |
| warn | missing_reference | 生产数据/comic_reference_plan_第4话.json | P016·端王赵佶：缺 全身/三视图参考（远景/全身动作格·单张头肩定妆不够） | identity | 按处方补该角色缺的视图/表情/服装参考并重建出图包。 |
| warn | same_frame_color_collision | 生产数据/comic_reference_plan_第4话.json | P027 多人同框主色撞色（易串脸）：CHAR_WANG_JIN↔CHAR_WANG_MOTHER（同主色「白」）——用互斥发色/服装主色/配饰强分，必要时拆反打。 | identity | 按处方补该角色缺的视图/表情/服装参考并重建出图包。 |
| warn | same_frame_color_collision | 生产数据/comic_reference_plan_第4话.json | P028 多人同框主色撞色（易串脸）：CHAR_WANG_JIN↔CHAR_WANG_MOTHER（同主色「白」）——用互斥发色/服装主色/配饰强分，必要时拆反打。 | identity | 按处方补该角色缺的视图/表情/服装参考并重建出图包。 |
| warn | same_frame_color_collision | 生产数据/comic_reference_plan_第4话.json | P029 多人同框主色撞色（易串脸）：CHAR_WANG_MOTHER↔CHAR_WANG_JIN（同主色「白」）——用互斥发色/服装主色/配饰强分，必要时拆反打。 | identity | 按处方补该角色缺的视图/表情/服装参考并重建出图包。 |
| warn | same_frame_color_collision | 生产数据/comic_reference_plan_第4话.json | P030 多人同框主色撞色（易串脸）：CHAR_WANG_JIN↔CHAR_WANG_MOTHER（同主色「白」）——用互斥发色/服装主色/配饰强分，必要时拆反打。 | identity | 按处方补该角色缺的视图/表情/服装参考并重建出图包。 |
| warn | same_frame_color_collision | 生产数据/comic_reference_plan_第4话.json | P032 多人同框主色撞色（易串脸）：CHAR_WANG_JIN↔CHAR_WANG_MOTHER（同主色「白」）——用互斥发色/服装主色/配饰强分，必要时拆反打。 | identity | 按处方补该角色缺的视图/表情/服装参考并重建出图包。 |
| warn | same_frame_color_collision | 生产数据/comic_reference_plan_第4话.json | P034 多人同框主色撞色（易串脸）：CHAR_WANG_JIN↔CHAR_GAO_QIU（同主色「白」）——用互斥发色/服装主色/配饰强分，必要时拆反打。 | identity | 按处方补该角色缺的视图/表情/服装参考并重建出图包。 |
| warn | same_frame_color_collision | 生产数据/comic_reference_plan_第4话.json | P035 多人同框主色撞色（易串脸）：CHAR_GAO_QIU↔CHAR_WANG_JIN（同主色「白」）——用互斥发色/服装主色/配饰强分，必要时拆反打。 | identity | 按处方补该角色缺的视图/表情/服装参考并重建出图包。 |
| warn | same_frame_color_collision | 生产数据/comic_reference_plan_第4话.json | P036 多人同框主色撞色（易串脸）：CHAR_GAO_QIU↔CHAR_WANG_JIN（同主色「白」）——用互斥发色/服装主色/配饰强分，必要时拆反打。 | identity | 按处方补该角色缺的视图/表情/服装参考并重建出图包。 |
| warn | same_frame_color_collision | 生产数据/comic_reference_plan_第4话.json | P038 多人同框主色撞色（易串脸）：CHAR_GAO_QIU↔CHAR_WANG_JIN（同主色「白」）——用互斥发色/服装主色/配饰强分，必要时拆反打。 | identity | 按处方补该角色缺的视图/表情/服装参考并重建出图包。 |
| warn | same_frame_color_collision | 生产数据/comic_reference_plan_第4话.json | P039 多人同框主色撞色（易串脸）：CHAR_GAO_QIU↔CHAR_WANG_JIN（同主色「白」）——用互斥发色/服装主色/配饰强分，必要时拆反打。 | identity | 按处方补该角色缺的视图/表情/服装参考并重建出图包。 |
| warn | same_frame_color_collision | 生产数据/comic_reference_plan_第4话.json | P040 多人同框主色撞色（易串脸）：CHAR_GAO_QIU↔CHAR_WANG_JIN（同主色「白」）——用互斥发色/服装主色/配饰强分，必要时拆反打。 | identity | 按处方补该角色缺的视图/表情/服装参考并重建出图包。 |
| warn | same_frame_color_collision | 生产数据/comic_reference_plan_第4话.json | P041 多人同框主色撞色（易串脸）：CHAR_GAO_QIU↔CHAR_WANG_JIN（同主色「白」）——用互斥发色/服装主色/配饰强分，必要时拆反打。 | identity | 按处方补该角色缺的视图/表情/服装参考并重建出图包。 |
| warn | same_frame_color_collision | 生产数据/comic_reference_plan_第4话.json | P042 多人同框主色撞色（易串脸）：CHAR_WANG_JIN↔CHAR_GAO_QIU（同主色「白」）——用互斥发色/服装主色/配饰强分，必要时拆反打。 | identity | 按处方补该角色缺的视图/表情/服装参考并重建出图包。 |
| warn | same_frame_color_collision | 生产数据/comic_reference_plan_第4话.json | P043 多人同框主色撞色（易串脸）：CHAR_WANG_JIN↔CHAR_GAO_QIU（同主色「白」）——用互斥发色/服装主色/配饰强分，必要时拆反打。 | identity | 按处方补该角色缺的视图/表情/服装参考并重建出图包。 |
| warn | same_frame_color_collision | 生产数据/comic_reference_plan_第4话.json | P044 多人同框主色撞色（易串脸）：CHAR_WANG_JIN↔CHAR_WANG_MOTHER（同主色「白」）——用互斥发色/服装主色/配饰强分，必要时拆反打。 | identity | 按处方补该角色缺的视图/表情/服装参考并重建出图包。 |
| warn | same_frame_color_collision | 生产数据/comic_reference_plan_第4话.json | P045 多人同框主色撞色（易串脸）：CHAR_WANG_JIN↔CHAR_WANG_MOTHER（同主色「白」）——用互斥发色/服装主色/配饰强分，必要时拆反打。 | identity | 按处方补该角色缺的视图/表情/服装参考并重建出图包。 |
| warn | same_frame_color_collision | 生产数据/comic_reference_plan_第4话.json | P046 多人同框主色撞色（易串脸）：CHAR_WANG_JIN↔CHAR_WANG_MOTHER（同主色「白」）——用互斥发色/服装主色/配饰强分，必要时拆反打。 | identity | 按处方补该角色缺的视图/表情/服装参考并重建出图包。 |
| warn | panel_post_qc_warn | 出图/第4话/panels/P002.png | P002 的落盘 post_qc=warn，需要人审签收或重抽。 | image | 放大查看 panel_qc 与原图；确认误报时在审查报告保留签收证据。 |
| warn | panel_post_qc_warn | 出图/第4话/panels/P003.png | P003 的落盘 post_qc=warn，需要人审签收或重抽。 | image | 放大查看 panel_qc 与原图；确认误报时在审查报告保留签收证据。 |
| warn | panel_post_qc_warn | 出图/第4话/panels/P009.png | P009 的落盘 post_qc=warn，需要人审签收或重抽。 | image | 放大查看 panel_qc 与原图；确认误报时在审查报告保留签收证据。 |
| warn | panel_post_qc_warn | 出图/第4话/panels/P012.png | P012 的落盘 post_qc=warn，需要人审签收或重抽。 | image | 放大查看 panel_qc 与原图；确认误报时在审查报告保留签收证据。 |
| warn | panel_post_qc_warn | 出图/第4话/panels/P016.png | P016 的落盘 post_qc=warn，需要人审签收或重抽。 | image | 放大查看 panel_qc 与原图；确认误报时在审查报告保留签收证据。 |
| warn | panel_post_qc_warn | 出图/第4话/panels/P021.png | P021 的落盘 post_qc=warn，需要人审签收或重抽。 | image | 放大查看 panel_qc 与原图；确认误报时在审查报告保留签收证据。 |
| warn | panel_style_outlier | 出图/第4话/panels/P004.png | 风格指纹内聚度 0.7898 明显低于本话中位 0.8326，疑似画风、细节密度或照片感跳变。 | image | 与全话 contact sheet 并排人审；若确实跳变，回 comic-image 用同一风格锚和参考图重抽该格。 |
| warn | panel_style_outlier | 出图/第4话/panels/P005.png | 风格指纹内聚度 0.7683 明显低于本话中位 0.8326，疑似画风、细节密度或照片感跳变。 | image | 与全话 contact sheet 并排人审；若确实跳变，回 comic-image 用同一风格锚和参考图重抽该格。 |
| warn | panel_style_outlier | 出图/第4话/panels/P007.png | 风格指纹内聚度 0.7043 明显低于本话中位 0.8326，疑似画风、细节密度或照片感跳变。 | image | 与全话 contact sheet 并排人审；若确实跳变，回 comic-image 用同一风格锚和参考图重抽该格。 |
| warn | panel_style_outlier | 出图/第4话/panels/P013.png | 风格指纹内聚度 0.7799 明显低于本话中位 0.8326，疑似画风、细节密度或照片感跳变。 | image | 与全话 contact sheet 并排人审；若确实跳变，回 comic-image 用同一风格锚和参考图重抽该格。 |
| warn | panel_style_outlier | 出图/第4话/panels/P014.png | 风格指纹内聚度 0.7800 明显低于本话中位 0.8326，疑似画风、细节密度或照片感跳变。 | image | 与全话 contact sheet 并排人审；若确实跳变，回 comic-image 用同一风格锚和参考图重抽该格。 |
| warn | panel_style_outlier | 出图/第4话/panels/P016.png | 风格指纹内聚度 0.7907 明显低于本话中位 0.8326，疑似画风、细节密度或照片感跳变。 | image | 与全话 contact sheet 并排人审；若确实跳变，回 comic-image 用同一风格锚和参考图重抽该格。 |
| warn | panel_style_outlier | 出图/第4话/panels/P023.png | 风格指纹内聚度 0.7441 明显低于本话中位 0.8326，疑似画风、细节密度或照片感跳变。 | image | 与全话 contact sheet 并排人审；若确实跳变，回 comic-image 用同一风格锚和参考图重抽该格。 |
| warn | panel_style_outlier | 出图/第4话/panels/P027.png | 风格指纹内聚度 0.7871 明显低于本话中位 0.8326，疑似画风、细节密度或照片感跳变。 | image | 与全话 contact sheet 并排人审；若确实跳变，回 comic-image 用同一风格锚和参考图重抽该格。 |
| warn | panel_style_outlier | 出图/第4话/panels/P028.png | 风格指纹内聚度 0.7607 明显低于本话中位 0.8326，疑似画风、细节密度或照片感跳变。 | image | 与全话 contact sheet 并排人审；若确实跳变，回 comic-image 用同一风格锚和参考图重抽该格。 |
| warn | panel_style_outlier | 出图/第4话/panels/P030.png | 风格指纹内聚度 0.7476 明显低于本话中位 0.8326，疑似画风、细节密度或照片感跳变。 | image | 与全话 contact sheet 并排人审；若确实跳变，回 comic-image 用同一风格锚和参考图重抽该格。 |
| warn | panel_style_outlier | 出图/第4话/panels/P032.png | 风格指纹内聚度 0.7775 明显低于本话中位 0.8326，疑似画风、细节密度或照片感跳变。 | image | 与全话 contact sheet 并排人审；若确实跳变，回 comic-image 用同一风格锚和参考图重抽该格。 |
| warn | panel_style_outlier | 出图/第4话/panels/P043.png | 风格指纹内聚度 0.7030 明显低于本话中位 0.8326，疑似画风、细节密度或照片感跳变。 | image | 与全话 contact sheet 并排人审；若确实跳变，回 comic-image 用同一风格锚和参考图重抽该格。 |
| warn | panel_style_outlier | 出图/第4话/panels/P044.png | 风格指纹内聚度 0.7901 明显低于本话中位 0.8326，疑似画风、细节密度或照片感跳变。 | image | 与全话 contact sheet 并排人审；若确实跳变，回 comic-image 用同一风格锚和参考图重抽该格。 |
| warn | panel_style_outlier | 出图/第4话/panels/P045.png | 风格指纹内聚度 0.7292 明显低于本话中位 0.8326，疑似画风、细节密度或照片感跳变。 | image | 与全话 contact sheet 并排人审；若确实跳变，回 comic-image 用同一风格锚和参考图重抽该格。 |
| warn | style_anchor_drift | 出图/共享/style_baseline.json | 本话整体指纹与风格锚图最高相似度仅 0.8730，风格锚可能已失去约束力。 | image | 并排比对锚图与本话 contact sheet；必要时更新风格锚或统一重抽。 |
| warn | outfit_fingerprint_low | 出图/第4话/panels/P027.png | CHAR_WANG_JIN outfit 指纹与参考图相似度偏低：score=0.394。这是色彩分布代理，需并排人审。 | image | 查看 character consistency contact sheet；如确实换脸/换发型/换服装，回 comic-image 用同一参考组重抽该格。 |
| warn | face_fingerprint_low | 出图/第4话/panels/P039.png | CHAR_WANG_JIN face 指纹与参考图相似度偏低：score=0.495。这是色彩分布代理，需并排人审。 | image | 查看 character consistency contact sheet；如确实换脸/换发型/换服装，回 comic-image 用同一参考组重抽该格。 |
| warn | outfit_fingerprint_low | 出图/第4话/panels/P042.png | CHAR_WANG_JIN outfit 指纹与参考图相似度偏低：score=0.404。这是色彩分布代理，需并排人审。 | image | 查看 character consistency contact sheet；如确实换脸/换发型/换服装，回 comic-image 用同一参考组重抽该格。 |
| warn | identity_similarity_engine_degraded | 生产数据/comic_character_consistency_第4话.json | CCIP 动漫身份 embedding 不可用，角色/生物相似度机检降级为色彩分布代理（同色调换脸/变形会漏报）。 | review | 独立 venv 安装 dghs-imgutils 后重跑 gate；在装好前必须以 VLM 并排裁决兜底身份轴。 |
| warn | vlm_judge_unadjudicated | 生产数据/comic_vlm_judge_tasks_第4话.json | VLM 并排判定任务包已生成 129 条但 0 条裁决——角色/生物身份、背景、道具三轴机检空转，画错生物形态这类漂移不会被拦。 | review | 由多模态 agent 逐条看图打分并写回 生产数据/comic_vlm_judge_verdicts_第4话.json 后重跑 gate。 |
